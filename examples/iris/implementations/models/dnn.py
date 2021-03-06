import tensorflow as tf


def create_estimator(run_config, model_config):
    columns = [
        tf.feature_column.numeric_column("sepal_length_normalized"),
        tf.feature_column.numeric_column("sepal_width_normalized"),
        tf.feature_column.numeric_column("petal_length_normalized"),
        tf.feature_column.numeric_column("petal_width_normalized"),
    ]

    return tf.estimator.DNNClassifier(
        feature_columns=columns,
        hidden_units=model_config["hparams"]["hidden_units"],
        n_classes=len(model_config["aggregates"]["class_index"]),
        config=run_config,
    )
