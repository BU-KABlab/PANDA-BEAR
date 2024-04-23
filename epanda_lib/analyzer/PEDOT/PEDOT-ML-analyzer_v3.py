import math
import numpy as np
import torch
import gpytorch
import pandas as pd
import random
from pyDOE2 import lhs
from scipy.stats.qmc import LatinHypercube
from gpytorch.models import ExactGP
from gpytorch.means import ConstantMean
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.distributions import MultivariateNormal
from gpytorch.mlls import ExactMarginalLogLikelihood
from scipy.stats import qmc
from sklearn.metrics import mean_squared_error
from tqdm import tqdm
import matplotlib.pyplot as plt
from IPython.display import display, clear_output
from torch.distributions.normal import Normal
from pathlib import Path

current_directory = Path(__file__).parent
training_directory = current_directory / "training_data"
file_path = training_directory / "MLTrainingData.csv"


class GPModel(ExactGP):
    def __init__(self, train_x, train_y, likelihood):
        super(GPModel, self).__init__(train_x, train_y, likelihood)
        self.mean_module = ConstantMean()
        self.covar_module = ScaleKernel(RBFKernel(ard_num_dims=3))
        self.covar_module.base_kernel.lengthscale = 1.0
        self.covar_module.outputscale = 1.0

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return MultivariateNormal(mean_x, covar_x)


# Scale inputs to the desired ranges
def scale_inputs(
    x,
    voltage_bounds,
    time_bounds,
    concentration_bounds,
    voltage_target,
    time_target,
    concentration_target,
):
    voltage, time, concentration = x[:, 0], x[:, 1], x[:, 2]

    voltage_scaled = voltage_target[0] + (
        (voltage - voltage_bounds[0])
        * (voltage_target[1] - voltage_target[0])
        / (voltage_bounds[1] - voltage_bounds[0])
    )

    time_scaled = time_target[0] + (
        (np.vectorize(math.log)(time) - math.log(time_bounds[0]))
        * (time_target[1] - time_target[0])
        / (math.log(time_bounds[1]) - math.log(time_bounds[0]))
    )

    concentration_scaled = concentration_target[0] + (
        (np.vectorize(math.log)(concentration) - math.log(concentration_bounds[0]))
        * (concentration_target[1] - concentration_target[0])
        / (math.log(concentration_bounds[1]) - math.log(concentration_bounds[0]))
    )

    x_scaled = np.stack((voltage_scaled, time_scaled, concentration_scaled), axis=1)
    return x_scaled


def convert_back_to_original(
    best_test_point_scaled,
    voltage_original=(0.8, 1.6),
    time_original=(1, 100),
    concentration_original=(0.01, 0.1),
    voltage_target=(0, 1),
    time_target=(0, 1),
    concentration_target=(0, 1),
):

    voltage = voltage_original[0] + (
        (best_test_point_scaled[0] - voltage_target[0])
        * (voltage_original[1] - voltage_original[0])
        / (voltage_target[1] - voltage_target[0])
    )

    time_scaled_back = time_target[0] + (
        (best_test_point_scaled[1] - time_target[0])
        * (time_target[1] - time_target[0])
        / (time_target[1] - time_target[0])
    )
    time = math.log(time_original[0]) + (
        time_scaled_back * (math.log(time_original[1]) - math.log(time_original[0]))
    )
    time = math.exp(time)

    concentration_scaled_back = concentration_target[0] + (
        (best_test_point_scaled[2] - concentration_target[0])
        * (concentration_target[1] - concentration_target[0])
        / (concentration_target[1] - concentration_target[0])
    )
    concentration = math.log(concentration_original[0]) + (
        concentration_scaled_back
        * (math.log(concentration_original[1]) - math.log(concentration_original[0]))
    )
    concentration = math.exp(concentration)

    return np.array([voltage, time, concentration])


# Import training data and convert to Pytorch tensors
data_df = pd.read_csv(file_path)
voltage = data_df["voltage"].values
time = data_df["time"].values
concentration = data_df["concentration"].values
response = data_df["deltaE"].values
bleachCP = data_df["bleachCP"].values

original_data = np.stack((voltage, time, concentration), axis=1)
x_scaled = scale_inputs(
    original_data,
    voltage_bounds=(0.8, 1.6),
    time_bounds=(1, 100),
    concentration_bounds=(0.01, 0.1),
    voltage_target=(0, 1),
    time_target=(0, 1),
    concentration_target=(0, 1),
)


def train_model(model, likelihood, optimizer, train_x, train_y, training_iter):
    model.train()
    likelihood.train()
    best_model = model.state_dict()
    losses = []

    for i in tqdm(range(training_iter), desc="Training"):
        optimizer.zero_grad()
        output = model(train_x)
        loss = -mll(output, train_y)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())


n_data = len(response)
predictions = np.zeros(n_data)
actuals = np.zeros(n_data)
best_validation_rmse = float("inf")
best_model = None

for i in tqdm(range(n_data)):
    train_indices = list(set(range(n_data)) - {i})
    test_index = i

    x_train, y_train = original_data[train_indices], response[train_indices]
    x_test, y_test = (
        original_data[test_index : test_index + 1],
        response[test_index : test_index + 1],
    )

    # Scale inputs
    x_train_scaled = scale_inputs(
        x_train,
        voltage_bounds=(0.8, 1.6),
        time_bounds=(1, 100),
        concentration_bounds=(0.01, 0.1),
        voltage_target=(0, 1),
        time_target=(0, 1),
        concentration_target=(0, 1),
    )
    x_test_scaled = scale_inputs(
        x_test,
        voltage_bounds=(0.8, 1.6),
        time_bounds=(1, 100),
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
    likelihood = gpytorch.likelihoods.GaussianLikelihood(noise=torch.tensor(0.002))
    likelihood.noise_covar.register_constraint(
        "raw_noise", gpytorch.constraints.GreaterThan(1e-4)
    )
    likelihood.noise_covar.noise = 1e-4
    likelihood.noise_covar.raw_noise.requires_grad_(True)
    model = GPModel(train_x, train_y, likelihood)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)  # Lower learning rate
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)
    # Train the model on the training set
    train_model(model, likelihood, optimizer, train_x, train_y, training_iter=500)

    # Evaluate on the test set
    model.eval()
    likelihood.eval()
    with torch.no_grad(), gpytorch.settings.fast_pred_var():
        observed_pred = likelihood(model(test_x))
        pred = observed_pred.mean.numpy()
        rmse = np.sqrt(mean_squared_error(test_y.numpy(), pred))
        if rmse < best_validation_rmse:
            best_validation_rmse = rmse
            best_model = model.state_dict()
    # Ensure pred is treated as a scalar
    if pred.size == 1:
        predictions[i] = pred.item()
    else:
        raise ValueError("Prediction `pred` is not a single value as expected.")

    actuals[i] = y_test[0]

rmse = np.sqrt(mean_squared_error(actuals, predictions))
print(f"LOOCV RMSE: {rmse}")


def save_model(model, optimizer, filename="model_state.pth"):
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "likelihood_state_dict": model.likelihood.state_dict(),
        },
        filename,
    )


save_model(model, optimizer, filename="pedot_gp_model_testing_v2.pth")

model.eval()
likelihood.eval()


def generate_and_scale_lhs_points(
    num_points,
    voltage_target=(0, 1),
    time_target=(0, 1),
    concentration_target=(0, 1),
    concentrations=[],
):
    combined_samples = []
    for concentration in concentrations:
        sampler = qmc.LatinHypercube(d=2)
        samples = sampler.random(n=num_points)

        samples[:, 0] = voltage_target[0] + (
            samples[:, 0] * (voltage_target[1] - voltage_target[0])
        )
        samples[:, 1] = time_target[0] + (
            samples[:, 1] * (time_target[1] - time_target[0])
        )
        scaled_concentration = np.full(
            (num_points, 1),
            concentration_target[0]
            + (concentration - 0.01)
            * (concentration_target[1] - concentration_target[0])
            / (0.1 - 0.01),
        )
        samples_with_concentration = np.hstack((samples, scaled_concentration))
        combined_samples.append(samples_with_concentration)

    combined_samples = np.vstack(combined_samples)
    return combined_samples


# Configuration for generating and scaling LHS points
voltage_target = (0, 1)
time_target = (0, 1)
concentration_target = (0, 1)
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

# Generate and scale LHS points
test_points_scaled = generate_and_scale_lhs_points(
    num_points, voltage_target, time_target, concentration_target, concentrations
)

# Convert to PyTorch tensor for use in model
test_x_scaled = torch.tensor(test_points_scaled, dtype=torch.float32)

# Assuming 'train_y' contains your observed target values and you're looking for the maximum.
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
        return ei.numpy()


ei = expected_improvement(model, test_x_scaled, current_best_response, likelihood)
best_point_index = np.argmax(ei)
best_test_point = test_points_scaled[best_point_index]

with torch.no_grad(), gpytorch.settings.fast_pred_var():
    best_test_point_tensor = torch.tensor(
        best_test_point, dtype=torch.float32
    ).unsqueeze(
        0
    )  # Add batch dimension
    predicted_distribution = likelihood(model(best_test_point_tensor))
    predicted_mean = predicted_distribution.mean.item()
    predicted_stddev = predicted_distribution.stddev.item()
print("best tst point in scalar values:", best_test_point)
best_test_point_original = convert_back_to_original(best_test_point)

print("Best Test Point in Original Values:", best_test_point_original)
print("Predicted Response at Best Test Point:", predicted_mean)
print("Standard Deviation of Prediction:", predicted_stddev)

precision = 3
rounded_best_test_point_original = [
    round(value, precision) for value in best_test_point_original
]
print("Best Test Point in Original Values:", rounded_best_test_point_original)
