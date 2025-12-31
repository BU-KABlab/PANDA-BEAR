# Using Analyzers

Analyzers process and analyze experiment results from the PANDA-BEAR system. They perform data analysis, generate visualizations, and can create new experiments based on analysis results.

**Navigation**: [Home](00-Home.md) | [Getting Started](01%20Getting-Started.md) | [Writing Protocols](03%20Writing-Protocols.md) | [Creating Generators](02%20Creating-Generators.md) | Using Analyzers

## Table of Contents

- [Analyzer Basics](#analyzer-basics)
- [Analyzer Structure](#analyzer-structure)
- [Creating an Analyzer](#creating-an-analyzer)
- [Running Analyzers](#running-analyzers)
- [Best Practices](#best-practices)
- [Next Steps](#next-steps)

## Analyzer Basics

Analyzers are Python modules that process experimental data from the PANDA database. An analyzer can:

1. Extract and process experiment results
2. Generate visualizations and metrics
3. Make decisions about future experiments
4. Generate new experiments based on analysis results

## Analyzer Structure

A basic analyzer consists of:

```python
"""
Analyzer: [Analyzer Name]
Author: [Your Name]
Date: [YYYY-MM-DD]
Description: [Brief description of what this analyzer does]
"""

# Import necessary libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from panda_lib import sql_tools
from panda_lib.experiments import ExperimentStatus

class MyAnalyzer:
    """Analyzer for processing specific experiment data."""
    
    def __init__(self, experiment_id=None, project_id=None):
        """Initialize the analyzer with experiment or project ID."""
        self.experiment_id = experiment_id
        self.project_id = project_id
        
    def analyze(self):
        """Analyze the experiment data."""
        # Fetch data from database
        # Process data
        # Generate metrics and visualizations
        # Return results
        
    def generate_next_experiments(self):
        """Generate new experiments based on analysis results."""
        # Create new experiment objects
        # Schedule them with the scheduler
        # Return information about the new experiments

# Function to be called by the analysis worker
def analyze_experiment(experiment_id):
    """Analyze a specific experiment."""
    analyzer = MyAnalyzer(experiment_id=experiment_id)
    results = analyzer.analyze()
    return results
```

## Example Analyzer

Here's an example of a simple analyzer that processes electrochemical data and generates plots:

```python
"""
Analyzer: Basic Electrochemical Analyzer
Author: Your Name
Date: 2025-05-16
Description: Analyzes chronoamperometry data and generates current vs time plots
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from panda_lib import sql_tools
from panda_lib.experiments import ExperimentStatus

class ElectrochemicalAnalyzer:
    """Analyzer for processing electrochemical experiment data."""
    
    def __init__(self, experiment_id=None, project_id=None):
        """Initialize the analyzer with experiment or project ID."""
        self.experiment_id = experiment_id
        self.project_id = project_id
        self.output_dir = "analysis_results"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def _get_experiment_data(self):
        """Fetch experiment data from the database."""
        query = f"""
        SELECT * FROM echem_results 
        WHERE experiment_id = {self.experiment_id}
        """
        return sql_tools.execute_query(query, fetch_all=True)
        
    def _get_experiment_metadata(self):
        """Fetch experiment metadata."""
        query = f"""
        SELECT * FROM experiments 
        WHERE experiment_id = {self.experiment_id}
        """
        return sql_tools.execute_query(query, fetch_one=True)
    
    def analyze(self):
        """Analyze chronoamperometry data."""
        # Get data from database
        data = self._get_experiment_data()
        metadata = self._get_experiment_metadata()
        
        if not data:
            print(f"No data found for experiment {self.experiment_id}")
            return None
            
        # Process the data
        df = pd.DataFrame(data)
        
        # For chronoamperometry data
        if 'time' in df.columns and 'current' in df.columns:
            # Create a plot
            plt.figure(figsize=(10, 6))
            plt.plot(df['time'], df['current'], 'b-')
            plt.xlabel('Time (s)')
            plt.ylabel('Current (A)')
            plt.title(f"Chronoamperometry - Experiment {self.experiment_id}")
            plt.grid(True)
            
            # Save the plot
            plot_path = os.path.join(self.output_dir, f"ca_plot_{self.experiment_id}.png")
            plt.savefig(plot_path)
            plt.close()
            
            # Calculate metrics
            max_current = df['current'].max()
            min_current = df['current'].min()
            avg_current = df['current'].mean()
            
            # Save metrics to database
            metrics_query = f"""
            INSERT INTO analysis_results 
            (experiment_id, max_current, min_current, avg_current) 
            VALUES ({self.experiment_id}, {max_current}, {min_current}, {avg_current})
            ON CONFLICT (experiment_id) DO UPDATE SET
            max_current = {max_current},
            min_current = {min_current},
            avg_current = {avg_current}
            """
            sql_tools.execute_query(metrics_query)
            
            # Update experiment status
            status_query = f"""
            UPDATE experiments 
            SET status = '{ExperimentStatus.ANALYZED.value}' 
            WHERE experiment_id = {self.experiment_id}
            """
            sql_tools.execute_query(status_query)
            
            return {
                "max_current": max_current,
                "min_current": min_current,
                "avg_current": avg_current,
                "plot_path": plot_path
            }
        
        return None

def analyze_experiment(experiment_id):
    """Function to be called by the analysis worker."""
    analyzer = ElectrochemicalAnalyzer(experiment_id=experiment_id)
    results = analyzer.analyze()
    return results
```

## Running Analyzers

Analyzers can be run in two ways:

### 1. Manual Analysis

You can manually run an analyzer on specific experiments:

```python
# Example of manual analysis
analyzer = ElectrochemicalAnalyzer(experiment_id=123)
results = analyzer.analyze()
print(results)
```

### 2. Automated Analysis through the Analysis Worker

The PANDA-BEAR system includes an analysis worker that can automatically run analyzers on completed experiments:

1. Place your analyzer in the analyzers directory specified in your config.ini
2. From the main menu, select option `10` to start the analysis loop
3. The system will automatically analyze any experiments with status set to "COMPLETED"

## Creating Advanced Analyzers

### Machine Learning Integration

For more advanced analysis, you can integrate machine learning:

```python
from sklearn.ensemble import RandomForestRegressor
import joblib

class MLAnalyzer:
    def __init__(self, project_id):
        self.project_id = project_id
        self.model_path = "models/rf_model.pkl"
        
    def train_model(self):
        # Fetch training data
        query = f"""
        SELECT * FROM analysis_results 
        JOIN experiments USING (experiment_id)
        WHERE project_id = {self.project_id}
        """
        data = sql_tools.execute_query(query, fetch_all=True)
        df = pd.DataFrame(data)
        
        # Prepare features and target
        X = df[['voltage', 'concentration', 'time']]
        y = df['max_current']
        
        # Train model
        model = RandomForestRegressor(n_estimators=100)
        model.fit(X, y)
        
        # Save model
        joblib.dump(model, self.model_path)
        
    def predict_optimal_params(self):
        # Load model
        model = joblib.load(self.model_path)
        
        # Generate parameter grid
        voltages = np.linspace(1.0, 2.0, 20)
        concentrations = np.linspace(0.1, 1.0, 10)
        times = np.linspace(600, 1800, 10)
        
        grid = np.array(np.meshgrid(voltages, concentrations, times)).T.reshape(-1, 3)
        predictions = model.predict(grid)
        
        # Find optimal parameters
        best_idx = np.argmax(predictions)
        best_params = grid[best_idx]
        
        return {
            "voltage": best_params[0],
            "concentration": best_params[1],
            "time": best_params[2],
            "predicted_current": predictions[best_idx]
        }
```

### Automated Experiment Generation

You can extend analyzers to automatically generate new experiments based on analysis results:

```python
def generate_next_experiments(self):
    # Get optimal parameters from model
    optimal_params = self.predict_optimal_params()
    
    # Create new experiments around the optimal point
    from panda_lib import scheduler
    from panda_lib.experiments import EchemExperimentBase
    
    next_experiment_id = scheduler.determine_next_experiment_id()
    
    # Create an experiment with optimal parameters
    experiment = EchemExperimentBase(
        experiment_id=next_experiment_id,
        protocol_id="optimized_protocol.py",
        # Other parameters including optimal_params values
        # ...
    )
    
    # Schedule the experiment
    scheduler.add_nonfile_experiments([experiment])
    
    return f"Generated new optimized experiment with ID {next_experiment_id}"
```

## Best Practices

1. **Modular Design**: Break down your analyzer into logical components for easier maintenance.

2. **Error Handling**: Include robust error handling to manage missing or corrupted data.

3. **Documentation**: Document your analyzer thoroughly, especially any metrics or algorithms.

4. **Data Visualization**: Include visualizations to help interpret results.

5. **Database Management**: Properly manage database connections to avoid resource leaks.

6. **Testing**: Test analyzers with sample data before deploying on real experimental results.

## Next Steps

With analyzers in place, you can complete the full experimental cycle from protocol development to data analysis. To learn more about other aspects of the PANDA-BEAR system, check out:

- [API Reference](API-Reference.md) for detailed information on the PANDA-BEAR library
- [Main Menu Reference](Main-Menu-Reference.md) for all available system functions
- [Writing Protocols](03%20Writing-Protocols.md) to understand how experiments are executed
- [Creating Generators](02%20Creating-Generators.md) to automate experiment creation
