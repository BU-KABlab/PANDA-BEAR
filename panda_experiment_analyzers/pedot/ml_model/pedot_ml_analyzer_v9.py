"""
Gaussian Process ML Model for Optimal PEDOT Electrodeposition
Version 9

This module implements a machine learning model to optimize PEDOT (poly(3,4-ethylenedioxythiophene))
electrodeposition parameters. It uses Gaussian Process Regression to predict and optimize
three key parameters:
1. Deposition voltage (V)
2. Deposition time (s)
3. EDOT concentration (M)

The model aims to maximize the electrochromic performance (ΔE₀₀) of the deposited PEDOT films.

Author: Harley Quinn
Date: 2024-05-02
"""

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import gpytorch
import numpy as np
import pandas as pd
import torch
from gpytorch.distributions import MultivariateNormal
from gpytorch.kernels import RBFKernel, ScaleKernel
from gpytorch.means import ConstantMean
from gpytorch.models import ExactGP
from scipy.stats import qmc
from sklearn.metrics import mean_squared_error
from tqdm import tqdm

# from tqdm.notebook import tqdm #use in jupyter notebook
from panda_experiment_analyzers.pedot.sql_ml_functions import (
    insert_best_test_point,
    model_iteration,
    select_ml_training_data,
)
from panda_lib.experiments.results import (
    ExperimentResultsRecord,
    insert_experiment_results,
)

# Ensure Intel MKL operations are permitted (required for some PyTorch operations)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from .exceptions import ModelLoadError, ModelSaveError, ParameterValidationError
from .logger_config import setup_logger
from .visualization import PEDOTVisualizer

logger = setup_logger()


class PEDOTGaussianProcess(ExactGP):
    """
    Gaussian Process model specifically designed for PEDOT electrodeposition optimization.

    This model uses a Radial Basis Function (RBF) kernel with Automatic Relevance
    Determination (ARD) to capture the relationships between deposition parameters
    and film performance.
    """

    def __init__(
        self,
        train_x: torch.Tensor,
        train_y: torch.Tensor,
        likelihood: gpytorch.likelihoods.Likelihood,
        lengthscale: float = 1.0,
        outputscale: float = 1.0,
        noise: float = 0.1,
    ):
        """
        Initialize the Gaussian Process model.

        Args:
            train_x: Input training data (deposition parameters)
            train_y: Target training data (ΔE₀₀ values)
            likelihood: GPyTorch likelihood function
            lengthscale: Initial lengthscale for the RBF kernel
            outputscale: Initial scale for the kernel output
            noise: Initial noise level for the likelihood
        """
        super().__init__(train_x, train_y, likelihood)

        # Mean function (constant mean)
        self.mean_module = ConstantMean()

        # Covariance function (RBF kernel with ARD)
        self.covar_module = ScaleKernel(RBFKernel(ard_num_dims=3))

        # Set initial hyperparameters
        self.covar_module.base_kernel.lengthscale = lengthscale
        self.covar_module.outputscale = outputscale
        self.likelihood.noise = noise

    def forward(self, x: torch.Tensor) -> MultivariateNormal:
        """
        Forward pass through the model.

        Args:
            x: Input tensor of shape (n_samples, n_features)

        Returns:
            MultivariateNormal distribution representing predictions
        """
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return MultivariateNormal(mean_x, covar_x)


@dataclass
class PEDOTParameters:
    """
    Configuration settings for PEDOT optimization.

    Defines the acceptable ranges for all parameters:
    - Voltage: How much electrical potential to apply (typically 0.6V to 1.8V)
    - Time: How long to run the deposition (typically 1s to 200s)
    - Concentration: How concentrated the EDOT solution is (typically 0.01M to 0.1M)

    The target_range defines how these values are normalized internally (usually 0 to 1).
    Default_concentrations provides a set of pre-defined concentration values that the system is capable of making.
    """

    voltage_bounds: Tuple[float, float] = (0.6, 1.8)
    time_bounds: Tuple[float, float] = (1, 200)
    concentration_bounds: Tuple[float, float] = (0.01, 0.1)
    target_range: Tuple[float, float] = (0, 1)
    default_concentrations: Sequence[float] = (
        0.027,
        0.023,
        0.020,
        0.017,
        0.013,
        0.010,
        0.085,
        0.070,
        0.055,
        0.040,
        0.025,
        0.030,
        0.100,
        0.088,
        0.077,
        0.065,
        0.053,
        0.042,
    )

    def validate(self) -> None:
        """Validate parameter values."""
        if self.voltage_bounds[0] >= self.voltage_bounds[1]:
            raise ParameterValidationError(
                "Invalid voltage bounds: min must be less than max"
            )
        if self.time_bounds[0] >= self.time_bounds[1]:
            raise ParameterValidationError(
                "Invalid time bounds: min must be less than max"
            )
        if self.concentration_bounds[0] >= self.concentration_bounds[1]:
            raise ParameterValidationError(
                "Invalid concentration bounds: min must be less than max"
            )
        if not all(
            self.target_range[0] <= c <= self.target_range[1]
            for c in self.default_concentrations
        ):
            raise ParameterValidationError(
                "Default concentrations must be within target range"
            )

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()


class PEDOTOptimizer:
    """
    The main optimization engine for PEDOT deposition.

    This class combines all the pieces needed to optimize PEDOT deposition:
    1. Data preprocessing (scaling parameters to suitable ranges)
    2. Model training (learning from existing data)
    3. Parameter optimization (finding the best new parameters to try)
    4. Result visualization (creating plots to understand predictions)

    The optimizer can be used to:
    - Load and save trained models
    - Train new models on experimental data
    - Perform cross-validation to evaluate model performance
    - Optimize deposition parameters to maximize performance
    - Generate visualization plots for model predictions

    The optimizer uses a Gaussian Process model to predict PEDOT performance.
    """

    def __init__(
        self,
        model_base_path: str,
        contourplots_path: str,
        params: Optional[PEDOTParameters] = None,
    ):
        """
        Initialize the PEDOT optimizer.

        Args:
            model_base_path: Path to save/load model checkpoints
            contourplots_path: Path to save visualization plots
            params: Optional configuration parameters for PEDOT optimization
        """
        if not Path(model_base_path).parent.exists():
            raise ParameterValidationError(
                f"Model base path directory does not exist: {model_base_path}"
            )
        if not Path(contourplots_path).exists():
            Path(contourplots_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created contourplots directory: {contourplots_path}")

        self.model_base_path = model_base_path
        self.contourplots_path = contourplots_path
        self.params = params or PEDOTParameters()
        self.visualizer = PEDOTVisualizer()
        logger.info("PEDOTOptimizer initialized successfully")

    def scale_inputs(self, x: np.ndarray) -> np.ndarray:
        """
        Uses linear scaling for voltage and log scaling for time and concentration
        to better handle their exponential nature.

        Args:
            x: Array of shape (n_samples, 3) containing [voltage, time, concentration]

        Returns:
            Array of normalized parameters
        """
        voltage, time, concentration = x[:, 0], x[:, 1], x[:, 2]

        # Linear scaling for voltage
        voltage_scaled = self._linear_scale(
            voltage, self.params.voltage_bounds, self.params.target_range
        )

        # Log scaling for time
        time_scaled = self._log_scale(
            time, self.params.time_bounds, self.params.target_range
        )

        # Log scaling for concentration
        concentration_scaled = self._log_scale(
            concentration, self.params.concentration_bounds, self.params.target_range
        )

        return np.stack((voltage_scaled, time_scaled, concentration_scaled), axis=1)

    @staticmethod
    def _linear_scale(
        x: np.ndarray, bounds: Tuple[float, float], target: Tuple[float, float]
    ) -> np.ndarray:
        """Helper function for linear scaling"""
        return target[0] + (x - bounds[0]) * (target[1] - target[0]) / (
            bounds[1] - bounds[0]
        )

    @staticmethod
    def _log_scale(
        x: np.ndarray, bounds: Tuple[float, float], target: Tuple[float, float]
    ) -> np.ndarray:
        """Helper function for logarithmic scaling"""
        return target[0] + (np.log(x) - np.log(bounds[0])) * (target[1] - target[0]) / (
            np.log(bounds[1]) - np.log(bounds[0])
        )

    def load_model(
        self, train_x: torch.Tensor, train_y: torch.Tensor
    ) -> Tuple[PEDOTGaussianProcess, gpytorch.likelihoods.GaussianLikelihood, float]:
        """
        Load a previously trained model from disk.

        Args:
            train_x: Training input data
            train_y: Training target data

        Returns:
            Tuple containing:
            - Loaded model
            - Model likelihood
            - Learning rate
        """
        counter = model_iteration()
        load_filename = f"{self.model_base_path}_{counter}.pth"

        logger.info(f"Attempting to load model from: {load_filename}")

        if not os.path.exists(load_filename):
            msg = f"No model found at {load_filename}"
            logger.error(msg)
            raise ModelLoadError(msg)

        try:
            saved_state = torch.load(load_filename)
            self._validate_saved_state(saved_state)

            likelihood = gpytorch.likelihoods.GaussianLikelihood()
            model = PEDOTGaussianProcess(train_x, train_y, likelihood)

            model.load_state_dict(saved_state["model_state_dict"])
            likelihood.load_state_dict(saved_state["likelihood_state_dict"])
            lr = saved_state["learning_rate"]

            logger.info(f"Successfully loaded model (iteration {counter})")
            return model, likelihood, lr

        except Exception as e:
            msg = f"Error loading model: {str(e)}"
            logger.error(msg)
            raise ModelLoadError(msg) from e

    def _validate_saved_state(self, state: Dict[str, Any]) -> None:
        """Validate saved state dictionary."""
        required_keys = {
            "model_state_dict",
            "optimizer_state_dict",
            "likelihood_state_dict",
            "learning_rate",
        }
        missing_keys = required_keys - state.keys()
        if missing_keys:
            raise ModelLoadError(
                f"Missing required keys in saved state: {missing_keys}"
            )

    def save_model(
        self, model: PEDOTGaussianProcess, optimizer: torch.optim.Optimizer
    ) -> Tuple[str, int]:
        """
        Save model state to disk and increment model counter.

        Args:
            model: Trained model to save
            optimizer: Optimizer used during training

        Returns:
            Tuple containing:
            - Path to saved model file
            - New model iteration number
        """
        counter = model_iteration()
        new_counter = counter + 1
        filename = f"{self.model_base_path}_{new_counter}.pth"

        logger.info(f"Attempting to save model to: {filename}")

        try:
            save_state = {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "likelihood_state_dict": model.likelihood.state_dict(),
                "learning_rate": optimizer.param_groups[0]["lr"],
            }

            # Create backup of previous model if it exists
            if os.path.exists(filename):
                backup_name = f"{filename}.backup"
                os.rename(filename, backup_name)
                logger.info(f"Created backup of existing model: {backup_name}")

            torch.save(save_state, filename)
            logger.info(f"Successfully saved model (iteration {new_counter})")
            return filename, new_counter

        except Exception as e:
            msg = f"Error saving model: {str(e)}"
            logger.error(msg)
            raise ModelSaveError(msg) from e

    def train_model(
        self,
        model: PEDOTGaussianProcess,
        likelihood: gpytorch.likelihoods.GaussianLikelihood,
        train_x: torch.Tensor,
        train_y: torch.Tensor,
        n_iterations: int = 500,
        learning_rate: float = 0.1,
    ) -> Tuple[PEDOTGaussianProcess, float]:
        """
        Train the model using existing experimental data:
        - What parameters were used (voltage, time, concentration)
        - What results were obtained (ΔE₀₀)

        The model learns patterns from this data and can then:
        - Predict results for new parameter combinations
        - Estimate how confident it is about these predictions

        The training process automatically adjusts its learning speed (learning_rate)
        to find the best balance between learning too slowly and too quickly.

        Args:
            model: Model to train
            likelihood: Model likelihood function
            train_x: Training input data
            train_y: Training target data
            n_iterations: Number of training iterations
            learning_rate: Initial learning rate

        Returns:
            Tuple containing:
            - Trained model
            - Final RMSE
        """
        if n_iterations < 1:
            raise ParameterValidationError("n_iterations must be positive")
        if learning_rate <= 0:
            raise ParameterValidationError("learning_rate must be positive")

        logger.info(f"Starting model training with {n_iterations} iterations")
        model.train()
        likelihood.train()

        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

        # Training loop with adaptive learning rate
        previous_loss = float("inf")
        for _ in tqdm(range(n_iterations), desc="Training"):
            optimizer.zero_grad()
            output = model(train_x)
            loss = -mll(output, train_y)
            loss.backward()
            optimizer.step()

            # Adaptive learning rate
            if loss.item() < previous_loss:
                learning_rate *= 0.95  # Decrease LR if improving
            else:
                learning_rate *= 1.05  # Increase LR if stuck

            for param_group in optimizer.param_groups:
                param_group["lr"] = learning_rate

            previous_loss = loss.item()

        # Calculate final RMSE
        model.eval()
        with torch.no_grad():
            predictions = model(train_x).mean
            rmse = torch.sqrt(torch.mean((predictions - train_y) ** 2))

        logger.info(f"Training completed. Final RMSE: {rmse.item():.4f}")
        return model, rmse.item()

    def perform_cross_validation(
        self,
        data: np.ndarray,
        response: np.ndarray,
        n_folds: int = -1,
        n_iterations: int = 500,
        initial_lr: float = 0.1,
    ) -> Tuple[float, List[float], List[float]]:
        """
        Test how reliable the model's predictions are by using cross-validation.

        Cross-validation works by:
            1. Temporarily hiding some data from the model
            2. Asking the model to predict those hidden results
            3. Comparing predictions with actual results
            4. Repeating this process multiple times

            This gives us a realistic estimate of:
            - How accurate the model's predictions are
            - How consistent its performance is
            - Whether it can generalize to new situations

            The RMSE (Root Mean Square Error) tells us the typical prediction error:
            - Lower RMSE means better predictions
            - Higher RMSE means less reliable predictions

        Perform leave-one-out cross validation if n_folds=-1, otherwise k-fold CV.

        Args:
            data: Input features array of shape (n_samples, n_features)
            response: Target values array of shape (n_samples,)
            n_folds: Number of CV folds (-1 for leave-one-out)
            n_iterations: Number of training iterations per fold
            initial_lr: Initial learning rate for optimization

        Returns:
            Tuple containing:
            - Overall RMSE across all folds
            - List of predictions for each test point
            - List of validation RMSEs for each fold
        """
        if n_folds == -1:
            n_folds = len(response)

        n_data = len(response)
        predictions = np.zeros(n_data)
        validation_rmses = []

        for i in tqdm(range(n_data), desc="Cross-validation"):
            # Split data into train/test
            train_indices = list(set(range(n_data)) - {i})
            test_index = i

            x_train, y_train = data[train_indices], response[train_indices]
            x_test, y_test = (
                data[test_index : test_index + 1],
                response[test_index : test_index + 1],
            )

            # Scale inputs
            x_train_scaled = self.scale_inputs(x_train)
            x_test_scaled = self.scale_inputs(x_test)

            # Convert to PyTorch tensors
            train_x = torch.tensor(x_train_scaled, dtype=torch.float32)
            train_y = torch.tensor(y_train, dtype=torch.float32)
            test_x = torch.tensor(x_test_scaled, dtype=torch.float32)
            test_y = torch.tensor(y_test, dtype=torch.float32)

            # Initialize model and likelihood
            likelihood = gpytorch.likelihoods.GaussianLikelihood()
            model = PEDOTGaussianProcess(train_x, train_y, likelihood)

            # Train model
            model, train_rmse = self.train_model(
                model=model,
                likelihood=likelihood,
                train_x=train_x,
                train_y=train_y,
                n_iterations=n_iterations,
                learning_rate=initial_lr,
            )

            # Evaluate on test set
            model.eval()
            likelihood.eval()
            with torch.no_grad(), gpytorch.settings.fast_pred_var():
                test_pred = likelihood(model(test_x))
                pred_mean = test_pred.mean.numpy()
                predictions[i] = pred_mean.item()

                # Calculate validation RMSE for this fold
                fold_rmse = np.sqrt(mean_squared_error(test_y.numpy(), pred_mean))
                validation_rmses.append(fold_rmse)

        # Calculate overall performance metrics
        overall_rmse = np.sqrt(mean_squared_error(response, predictions))

        print("Cross-validation complete:")
        print(f"Overall RMSE: {overall_rmse:.4f}")
        print(
            f"Mean fold RMSE: {np.mean(validation_rmses):.4f} ± {np.std(validation_rmses):.4f}"
        )

        return overall_rmse, predictions, validation_rmses

    def plot_and_save_results(
        self,
        best_point: np.ndarray,
        test_points: np.ndarray,
        ei_values: np.ndarray,
        std_dev_values: np.ndarray,
        mean_values: np.ndarray,
        save_path: str,
    ) -> Tuple[Path, ...]:
        """Plot and save visualization results."""
        mask = np.isclose(test_points[:, 2], best_point[2], rtol=1e-3)

        voltage_values = test_points[mask, 0]
        time_values = test_points[mask, 1]
        ei_masked = ei_values[mask]
        std_dev_masked = std_dev_values[mask]
        mean_masked = mean_values[mask]

        fig = self.visualizer.create_contour_plots(
            voltage_values=voltage_values,
            time_values=time_values,
            ei_values=ei_masked,
            std_dev_values=std_dev_masked,
            mean_values=mean_masked,
            concentration=best_point[2],
        )

        return self.visualizer.save_plots(fig, save_path)

    def optimize_parameters(
        self,
        model: PEDOTGaussianProcess,
        likelihood: gpytorch.likelihoods.GaussianLikelihood,
        current_best: float,
        num_candidates: int = 50000,
    ) -> Tuple[np.ndarray, float, float]:
        """
        Find optimal deposition parameters using Expected Improvement (EI).

        Args:
            model: Trained model
            likelihood: Model likelihood
            current_best: Current best observed performance
            num_candidates: Number of candidate points to evaluate

        Returns:
            Tuple containing:
            - Optimal parameters [voltage, time, concentration]
            - Predicted mean performance
            - Predicted uncertainty
        """
        model.eval()
        likelihood.eval()

        # Generate candidate points using Latin Hypercube Sampling
        candidates = self.generate_candidates(num_candidates)
        candidates_tensor = torch.tensor(candidates, dtype=torch.float32)

        # Calculate Expected Improvement
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            predictions = likelihood(model(candidates_tensor))
            mean = predictions.mean
            std = predictions.stddev

            # Expected Improvement calculation
            z = (mean - current_best) / std
            ei = (mean - current_best) * torch.distributions.Normal(0, 1).cdf(
                z
            ) + std * torch.distributions.Normal(0, 1).log_prob(z).exp()

            # Find best candidate
            best_idx = torch.argmax(ei)
            best_candidate = candidates[best_idx]
            predicted_mean = mean[best_idx].item()
            predicted_std = std[best_idx].item()

        return best_candidate, predicted_mean, predicted_std

    def generate_candidates(
        self, num_points: int, concentrations: Optional[Sequence[float]] = None
    ) -> np.ndarray:
        """Generate candidate points using Latin Hypercube Sampling"""
        concentrations = concentrations or self.params.default_concentrations
        return self._generate_lhs_points(num_points, concentrations)

    def _generate_lhs_points(
        self, num_points: int, concentrations: Sequence[float]
    ) -> np.ndarray:
        """Internal method for Latin Hypercube Sampling point generation"""
        combined_samples = []
        for concentration in concentrations:
            sampler = qmc.LatinHypercube(d=2)
            samples = sampler.random(n=num_points)
            samples[:, 0] = self.params.target_range[0] + (
                samples[:, 0]
                * (self.params.target_range[1] - self.params.target_range[0])
            )
            samples[:, 1] = self.params.target_range[0] + (
                samples[:, 1]
                * (self.params.target_range[1] - self.params.target_range[0])
            )
            scaled_concentration = np.full(
                (num_points, 1),
                self.params.target_range[0]
                + (concentration - self.params.concentration_bounds[0])
                * (self.params.target_range[1] - self.params.target_range[0])
                / (
                    self.params.concentration_bounds[1]
                    - self.params.concentration_bounds[0]
                ),
            )
            samples_with_concentration = np.hstack((samples, scaled_concentration))
            combined_samples.append(samples_with_concentration)

        combined_samples = np.vstack(combined_samples)
        return combined_samples

    def convert_parameters(
        self, scaled_params: np.ndarray, to_original: bool = True
    ) -> np.ndarray:
        """Convert parameters between scaled and original space"""
        if to_original:
            return self._convert_to_original(scaled_params)
        return self.scale_inputs(scaled_params)

    def _convert_to_original(self, scaled_params: np.ndarray) -> np.ndarray:
        """Internal method for converting scaled parameters to original space"""
        voltage = self.params.voltage_bounds[0] + (
            (scaled_params[0] - self.params.target_range[0])
            * (self.params.voltage_bounds[1] - self.params.voltage_bounds[0])
            / (self.params.target_range[1] - self.params.target_range[0])
        )

        time_scaled_back = self.params.target_range[0] + (
            (scaled_params[1] - self.params.target_range[0])
            * (self.params.target_range[1] - self.params.target_range[0])
            / (self.params.target_range[1] - self.params.target_range[0])
        )
        time = math.log(self.params.time_bounds[0]) + (
            time_scaled_back
            * (
                math.log(self.params.time_bounds[1])
                - math.log(self.params.time_bounds[0])
            )
        )
        time = math.exp(time)

        concentration_scaled_back = self.params.target_range[0] + (
            (scaled_params[2] - self.params.target_range[0])
            * (self.params.target_range[1] - self.params.target_range[0])
            / (self.params.target_range[1] - self.params.target_range[0])
        )
        concentration = math.log(self.params.concentration_bounds[0]) + (
            concentration_scaled_back
            * (
                math.log(self.params.concentration_bounds[1])
                - math.log(self.params.concentration_bounds[0])
            )
        )
        concentration = math.exp(concentration)

        return np.array([voltage, time, concentration])


def get_next_filename(base_path, extensions):
    """Functions to increment the filenames"""
    counter = 1
    while True:
        exists = False
        for ext in extensions:
            if os.path.exists(f"{base_path}_{counter}.{ext}"):
                exists = True
                break
        if not exists:
            return f"{base_path}_{counter}"
        counter += 1


def main(
    model_base_path: str,
    contourplots_path: str,
    experiment_id: int = 0,
) -> Tuple[float, float, float, float, float, str, int]:
    """
    Main execution function for PEDOT parameter optimization.

    Args:
        model_base_path: Path to save/load model checkpoints
        contourplots_path: Path to save visualization plots
        experiment_id: Unique identifier for the experiment

    Returns:
        Tuple containing:
        - Optimized deposition voltage (V)
        - Optimized deposition time (s)
        - Optimized EDOT concentration (M)
        - Predicted mean performance (ΔE₀₀)
        - Predicted uncertainty
        - Path to generated contour plots
        - Model iteration ID
    """
    optimizer = PEDOTOptimizer(model_base_path, contourplots_path)

    # Load and preprocess training data
    data_df = select_ml_training_data()
    voltage = data_df["voltage"].values
    time = data_df["time"].values
    concentration = data_df["concentration"].values
    response = data_df["deltaE"].values

    original_data = np.stack((voltage, time, concentration), axis=1)

    n_data = len(response)
    predictions = np.zeros(n_data)
    actuals = np.zeros(n_data)
    best_validation_rmse = float("inf")
    # best_model = None
    previous_rmse = float("inf")

    for i in tqdm(range(n_data)):
        train_indices = list(set(range(n_data)) - {i})
        test_index = i

        x_train, y_train = original_data[train_indices], response[train_indices]
        x_test, y_test = (
            original_data[test_index : test_index + 1],
            response[test_index : test_index + 1],
        )

        # Scale inputs
        x_train_scaled = optimizer.scale_inputs(
            x_train,
            voltage_bounds=(0.6, 1.8),
            time_bounds=(1, 200),
            concentration_bounds=(0.01, 0.1),
            voltage_target=(0, 1),
            time_target=(0, 1),
            concentration_target=(0, 1),
        )
        x_test_scaled = optimizer.scale_inputs(
            x_test,
            voltage_bounds=(0.6, 1.8),
            time_bounds=(1, 200),
            concentration_bounds=(0.01, 0.1),
            voltage_target=(0, 1),
            time_target=(0, 1),
            concentration_target=(0, 1),
        )

        # Convert to PyTorch tensors
        train_x = torch.tensor(x_train_scaled, dtype=torch.float32)
        train_y = torch.tensor(y_train, dtype=torch.float32)
        test_x = torch.tensor(x_test_scaled, dtype=torch.float32)
        test_y = torch.tensor(y_test, dtype=torch.float32)

        # Set hyperparameters and call model
        # likelihood = gpytorch.likelihoods.GaussianLikelihood(noise=torch.tensor(noise))
        # model = GPModel(train_x, train_y, likelihood, lengthscale=lengthscale, outputscale=outputscale)
        model, likelihood, lr = optimizer.load_model(model_base_path, train_x, train_y)

        alg_optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        # Train the model on the training set
        optimizer.train_model(
            model, likelihood, alg_optimizer, train_x, train_y, training_iter=500
        )

        # Evaluate on the test set
        model.eval()
        likelihood.eval()
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            observed_pred = likelihood(model(test_x))
            pred = observed_pred.mean.numpy()
            rmse = np.sqrt(mean_squared_error(test_y.numpy(), pred))
            if rmse < best_validation_rmse:
                best_validation_rmse = rmse
                # best_model = model.state_dict()

        if rmse < previous_rmse:
            lr *= 0.95
        else:
            lr *= 1.05
        for param_group in alg_optimizer.param_groups:
            param_group["lr"] = lr

        previous_rmse = rmse

        if pred.size == 1:
            predictions[i] = pred.item()
        else:
            raise ValueError("Prediction `pred` is not a single value as expected.")

        actuals[i] = y_test[0]

    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    print(f"RMSE: {rmse}")

    _, model_id = optimizer.save_model(model, alg_optimizer, model_base_path)

    model.eval()
    likelihood.eval()

    # Configuration for generating and scaling LHS points
    concentrations = [
        0.027,
        0.023,
        0.020,
        0.017,
        0.013,
        0.010,
        0.085,
        0.070,
        0.055,
        0.040,
        0.025,
        0.030,
        0.100,
        0.088,
        0.077,
        0.065,
        0.053,
        0.042,
    ]
    num_points = 50000
    test_points_scaled = optimizer.generate_candidates(num_points, concentrations)
    test_x_scaled = torch.tensor(test_points_scaled, dtype=torch.float32)
    current_best_response = train_y.max().item()

    def expected_improvement(model, test_points_scaled, current_best, likelihood):
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            observed_pred = likelihood(model(test_points_scaled))
            mean = observed_pred.mean
            std_dev = observed_pred.stddev
            z = (mean - current_best) / std_dev
            ei = (mean - current_best) * torch.distributions.Normal(0, 1).cdf(
                z
            ) + std_dev * torch.distributions.Normal(0, 1).log_prob(z).exp()
            return ei.numpy(), std_dev.numpy(), mean.numpy()

    ei, std_dev, mean = expected_improvement(
        model, test_x_scaled, current_best_response, likelihood
    )
    best_point_index = np.argmax(ei)
    best_test_point = test_points_scaled[best_point_index]

    with torch.no_grad(), gpytorch.settings.fast_pred_var():
        best_test_point_tensor = torch.tensor(
            best_test_point, dtype=torch.float32
        ).unsqueeze(0)  # Add batch dimension
        predicted_distribution = likelihood(model(best_test_point_tensor))
        predicted_mean = predicted_distribution.mean.item()
        predicted_stddev = predicted_distribution.stddev.item()
    print("Best Test Point in scalar values:", best_test_point)
    best_test_point_original = optimizer.convert_parameters(best_test_point)

    print("Best Test Point in Original Values:", best_test_point_original)
    print("Predicted Response at Best Test Point:", predicted_mean)
    print("Standard Deviation of Prediction:", predicted_stddev)

    precision = 3
    rounded_best_test_point_original = [
        round(value, precision) for value in best_test_point_original
    ]
    print("Best Test Point in Original Values:", rounded_best_test_point_original)

    # Unpack values
    v_dep, t_dep, edot_concentration = rounded_best_test_point_original

    df = pd.DataFrame(
        {
            "Model ID": [model_id],
            "Experiment ID": [experiment_id],
            "Best Test Point Scalar": [best_test_point],
            "Best Test Point Original": [best_test_point_original],
            "Best Test Point": [rounded_best_test_point_original],
            "v_dep": [v_dep],
            "t_dep": [t_dep],
            "edot_concentration": [edot_concentration],
            "Predicted Response": [predicted_mean],
            "Standard Deviation": [predicted_stddev],
            "Models current RMSE": [rmse],
        }
    )

    insert_best_test_point(df)
    mask = np.isclose(
        test_points_scaled[:, 2], test_points_scaled[best_point_index, 2], rtol=1e-3
    )

    voltage_values = test_points_scaled[mask, 0]
    time_values = test_points_scaled[mask, 1]
    ei_values = ei[mask]
    std_dev_values = std_dev[mask]
    mean_values = mean[mask]
    fig = optimizer.visualizer.create_contour_plots(
        voltage_values=voltage_values,
        time_values=time_values,
        ei_values=ei_values,
        std_dev_values=std_dev_values,
        mean_values=mean_values,
        concentration=edot_concentration,
    )

    contourplots_filename = get_next_filename(
        contourplots_path, extensions=["svg", "png"]
    )
    paths = optimizer.visualizer.save_plots(fig, contourplots_filename)
    plot_path = str(paths[1])  # Use PNG path for database

    # Save the results to results
    to_be_inserted = [
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Deposition_Voltage",
            result_value=v_dep,
            context="pedot ml output",
        ),
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Deposition_Time",
            result_value=t_dep,
            context="pedot ml output",
        ),
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Concentration",
            result_value=edot_concentration,
            context="pedot ml output",
        ),
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Predicted_Mean",
            result_value=predicted_mean,
            context="pedot ml output",
        ),
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Predicted_Uncertainty",
            result_value=predicted_stddev,
            context="pedot ml output",
        ),
        ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="PEDOT_Contour_Plots",
            result_value=plot_path,
            context="pedot ml output",
        ),
    ]

    insert_experiment_results(to_be_inserted)

    return (
        v_dep,
        t_dep,
        edot_concentration,
        predicted_mean,
        predicted_stddev,
        plot_path,
        model_id,
    )


if __name__ == "__main__":
    # Example usage with test paths
    TEST_MODEL_BASE_PATH = "pedot_gp_model_v9"
    TEST_CONTOURPLOTS_PATH = "contourplots"

    main(
        model_base_path=TEST_MODEL_BASE_PATH,
        contourplots_path=TEST_CONTOURPLOTS_PATH,
        experiment_id=1,
    )
