"""_summary_"""
import os
import experiment_class as Experiment

for i in range(3,5):
    filename = f'test{i}.json'
    filepath = os.path.join(os.getcwd(),"code", "experiment_queue", filename)
    test = Experiment.make_test_value()
    test.filename = filename
    serialized_test = Experiment.RootModel[Experiment.Experiment](test).model_dump_json(indent=4)
    with open(filepath, 'w', encoding= "UTF-8") as f:
        f.write(serialized_test)
