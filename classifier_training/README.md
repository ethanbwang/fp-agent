# Classifier Training

This repository contains source code for getting data from the database, processing and featurizing the data, training a multi-class classifier,
and evaluating and analyzing the classifier.

## Requirements

### Dependencies

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

### Setup

This repository uses [uv](https://docs.astral.sh/uv/) to manage dependencies.
1. Create virtual environment
    ```bash
    uv init
    ```
2. Install dependencies
    ```bash
    uv sync
    ```

### Environment Variables

`DATABASE_URL`: Your database url.

`PROJECT_ROOT`: Path to root directory of the repository.

## Dataset

### Raw Data

The raw data can be found at [https://osf.io/j6b5p/overview?view_only=ac4ad89fbde540269aaaa85a2249cad6](https://osf.io/j6b5p/overview?view_only=ac4ad89fbde540269aaaa85a2249cad6). Helper functions can be used to load them into objects (located in [data_processing.py](src/classifier_training/data_processing.py)). Raw data is stored in JSON format:

```json
    {
        "Atlas Agent": [
            {
                "fpjs_data": [
                    {
                        "req_headers": "<headers>",
                        "req_body": "<body>",
                    }, ...
                ],
                "behavioral_data": [
                    {
                        "req_headers": "<headers>",
                        "req_body": "<body>",
                    }, ...
                ],
                "source": {
                    "website_version": "<website_version>",
                    "class_label": "<class_label>",
                    "task_name": "<task_name>",
                    "trial_index": "<trial_index>",
                    "start_time": "<start_time>",
                    "end_time": "<end_time>",
                    "source_file": "<source_file>",
                }
            }, ...
        ],
        "Browser Use": [...],
        ...
    }
```

The `source_file` key in `source` can be ignored; it was used to help identify the trial during the study.

### Processed Data

The processed data can be found at [](). Helper functions are located in [common.py](src/classifier_training/common.py). Processed data is stored in JSON format as well:

```json
{
    "Atlas Agent": {
        "<source_str>": {
            "fpjs": <browser_fingerprint_fv>,
            "behavioral": <behavioral_fingerprint_fv>
        }, ...
    },
    "Browser Use": {
        ...
    }, ...
}
```

## Training

To train the classifier, use `TrainingPipeline` in [classifier.py](src/classifier_training/classifier.py).

```python
from classifier_training.classifier import TrainingPipeline

training_pipeline = TrainingPipeline(
    dataset_file=<dataset_path>,
    split_file=<split_path>,
    feature_type=<feature_type>,
    removed_classes=<removed_classes>,
)

training_pipeline.train_model(
    model_file=<model_file>,
    max_depth=<max_depth>,
    learning_rate=<learning_rate>,
    n_estimators=<n_estimators>,
    random_state=<random_state>,
)
```

An example use case is in [ablation_trainer.py](src/classifier_training/ablation_trainer.py).
