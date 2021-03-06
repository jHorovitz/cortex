# Copyright 2019 Cortex Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

import spark_util

from pyspark.sql.types import *
from pyspark.sql import Row
from py4j.protocol import Py4JJavaError

pytestmark = pytest.mark.usefixtures("spark")
import pyspark.sql.functions as F
from mock import MagicMock, call
from lib.exceptions import UserException


def test_compare_column_schemas():
    expected = StructType(
        [
            StructField("a_float", FloatType()),
            StructField("b_long", LongType()),
            StructField("c_str", StringType()),
        ]
    )

    missing_col = StructType(
        [StructField("a_float", FloatType()), StructField("b_long", LongType())]
    )

    assert spark_util.compare_column_schemas(expected, missing_col) == False

    incorrect_type = StructType(
        [
            StructField("b_long", LongType()),
            StructField("a_float", FloatType()),
            StructField("c_str", LongType()),
        ]
    )

    assert spark_util.compare_column_schemas(expected, incorrect_type) == False

    actual = StructType(
        [
            StructField("b_long", LongType()),
            StructField("a_float", FloatType()),
            StructField("c_str", StringType()),
        ]
    )

    assert spark_util.compare_column_schemas(expected, actual) == True


def test_get_expected_schema_from_context_csv(ctx_obj, get_context):
    ctx_obj["environment"] = {
        "data": {"type": "csv", "schema": ["income", "years_employed", "prior_default"]}
    }
    ctx_obj["raw_features"] = {
        "income": {"name": "income", "type": "FLOAT_FEATURE", "required": True, "id": "-"},
        "years_employed": {
            "name": "years_employed",
            "type": "INT_FEATURE",
            "required": False,
            "id": "-",
        },
        "prior_default": {
            "name": "prior_default",
            "type": "STRING_FEATURE",
            "required": True,
            "id": "-",
        },
    }

    ctx = get_context(ctx_obj)

    expected_output = StructType(
        [
            StructField("years_employed", LongType(), True),
            StructField("income", FloatType(), False),
            StructField("prior_default", StringType(), False),
        ]
    )

    actual = spark_util.expected_schema_from_context(ctx)
    assert spark_util.compare_column_schemas(actual, expected_output) == True


def test_get_expected_schema_from_context_parquet(ctx_obj, get_context):
    ctx_obj["environment"] = {
        "data": {
            "type": "parquet",
            "schema": [
                {"column_name": "a_str", "feature_name": "a_str"},
                {"column_name": "b_float", "feature_name": "b_float"},
                {"column_name": "c_long", "feature_name": "c_long"},
            ],
        }
    }
    ctx_obj["raw_features"] = {
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": "-"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "-"},
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": "-"},
    }

    ctx = get_context(ctx_obj)

    expected_output = StructType(
        [
            StructField("c_long", LongType(), True),
            StructField("b_float", FloatType(), False),
            StructField("a_str", StringType(), False),
        ]
    )

    actual = spark_util.expected_schema_from_context(ctx)
    assert spark_util.compare_column_schemas(actual, expected_output) == True


def test_read_csv_valid(spark, write_csv_file, ctx_obj, get_context):
    csv_str = "\n".join(["a,0.1,", "b,1,1", "c,1.1,4"])

    path_to_file = write_csv_file(csv_str)

    ctx_obj["environment"] = {
        "data": {"type": "csv", "path": path_to_file, "schema": ["a_str", "b_float", "c_long"]}
    }

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": "-"},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": "-"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "-"},
    }

    assert spark_util.read_csv(get_context(ctx_obj), spark).count() == 3


def test_read_csv_invalid_type(spark, write_csv_file, ctx_obj, get_context):
    csv_str = "\n".join(["a,0.1,", "b,1,1", "c,1.1,4"])

    path_to_file = write_csv_file(csv_str)

    ctx_obj["environment"] = {
        "data": {"type": "csv", "path": path_to_file, "schema": ["a_str", "b_long", "c_long"]}
    }

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": "-"},
        "b_long": {"name": "b_long", "type": "INT_FEATURE", "required": True, "id": "-"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "-"},
    }

    with pytest.raises(Py4JJavaError):
        spark_util.ingest(get_context(ctx_obj), spark).collect()


def test_value_checker_required():
    raw_feature_config = {"name": "a_str", "type": "STRING_FEATURE", "required": True}
    results = list(spark_util.value_checker(raw_feature_config))
    results[0]["cond_col"] = str(results[0]["cond_col"]._jc)

    assert results == [
        {
            "col_name": "a_str",
            "cond_name": "required",
            "cond_col": str(F.col("a_str").isNull()._jc),
            "positive_cond_str": str(F.col("a_str").isNotNull()._jc),
        }
    ]


def test_value_checker_not_required():
    raw_feature_config = {"name": "a_str", "type": "STRING_FEATURE", "required": False}
    results = list(spark_util.value_checker(raw_feature_config))
    assert len(results) == 0


def test_value_checker_values():
    raw_feature_config = {
        "name": "a_long",
        "type": "INT_FEATURE",
        "values": [1, 2, 3],
        "required": True,
    }
    results = sorted(spark_util.value_checker(raw_feature_config), key=lambda x: x["cond_name"])
    for result in results:
        result["cond_col"] = str(result["cond_col"]._jc)

    assert results == [
        {
            "col_name": "a_long",
            "cond_name": "required",
            "cond_col": str(F.col("a_long").isNull()._jc),
            "positive_cond_str": str(F.col("a_long").isNotNull()._jc),
        },
        {
            "col_name": "a_long",
            "cond_name": "values",
            "cond_col": str((F.col("a_long").isin([1, 2, 3]) == False)._jc),
            "positive_cond_str": str(F.col("a_long").isin([1, 2, 3])._jc),
        },
    ]


def test_value_checker_min_max():
    raw_feature_config = {"name": "a_long", "type": "INT_FEATURE", "min": 1, "max": 2}
    results = sorted(spark_util.value_checker(raw_feature_config), key=lambda x: x["cond_name"])
    for result in results:
        result["cond_col"] = str(result["cond_col"]._jc)

    assert results == [
        {
            "col_name": "a_long",
            "cond_name": "max",
            "cond_col": ("(a_long > 2)"),
            "positive_cond_str": ("(a_long <= 2)"),
        },
        {
            "col_name": "a_long",
            "cond_name": "min",
            "cond_col": ("(a_long < 1)"),
            "positive_cond_str": ("(a_long >= 1)"),
        },
    ]


def test_value_check_data_valid(spark, ctx_obj, get_context):
    data = [("a", 0.1, None), ("b", 1.0, None), (None, 1.1, 0)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", LongType()),
        ]
    )

    df = spark.createDataFrame(data, schema)

    ctx_obj["raw_features"] = {
        "a_str": {
            "name": "a_str",
            "type": "STRING_FEATURE",
            "required": False,
            "values": ["a", "b"],
            "id": 1,
        },
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": 2},
        "c_long": {
            "name": "c_long",
            "type": "INT_FEATURE",
            "required": False,
            "max": 1,
            "min": 0,
            "id": 3,
        },
    }

    ctx = get_context(ctx_obj)

    assert len(spark_util.value_check_data(ctx, df)) == 0


def test_value_check_data_invalid_null_value(spark, ctx_obj, get_context):
    data = [("a", None, None), ("b", 1.0, None), ("c", 1.1, 1)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", LongType()),
        ]
    )

    df = spark.createDataFrame(data, schema)

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": 1},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": 2},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "max": 1, "min": 0, "id": 3},
    }

    ctx = get_context(ctx_obj)
    validations = spark_util.value_check_data(ctx, df)
    assert validations == {"b_float": [("(b_float IS NOT NULL)", 1)]}


def test_value_check_data_invalid_out_of_range(spark, ctx_obj, get_context):
    data = [("a", 2.3, None), ("b", 1.0, None), ("c", 1.1, 4)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", LongType()),
        ]
    )

    df = spark.createDataFrame(data, schema)

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": 1},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": 2},
        "c_long": {
            "name": "c_long",
            "type": "INT_FEATURE",
            "required": False,
            "max": 1,
            "min": 0,
            "id": 3,
        },
    }

    ctx = get_context(ctx_obj)

    validations = spark_util.value_check_data(ctx, df)
    assert validations == {"c_long": [("(c_long <= 1)", 1)]}


def test_ingest_parquet_valid(spark, write_parquet_file, ctx_obj, get_context):
    data = [("a", 0.1, None), ("b", 1.0, None), ("c", 1.1, 4)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", LongType()),
        ]
    )

    path_to_file = write_parquet_file(spark, data, schema)

    ctx_obj["environment"] = {
        "data": {
            "type": "parquet",
            "path": path_to_file,
            "schema": [
                {"column_name": "a_str", "feature_name": "a_str"},
                {"column_name": "b_float", "feature_name": "b_float"},
                {"column_name": "c_long", "feature_name": "c_long"},
            ],
        }
    }

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": "1"},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": "2"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "3"},
    }

    assert spark_util.ingest(get_context(ctx_obj), spark).count() == 3


def test_ingest_parquet_type_mismatch(spark, write_parquet_file, ctx_obj, get_context):
    data = [("a", 0.1, None), ("b", 1.0, None), ("c", 1.1, 4.0)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", FloatType()),
        ]
    )

    path_to_file = write_parquet_file(spark, data, schema)

    ctx_obj["environment"] = {
        "data": {
            "type": "parquet",
            "path": path_to_file,
            "schema": [
                {"column_name": "a_str", "feature_name": "a_str"},
                {"column_name": "b_float", "feature_name": "b_float"},
                {"column_name": "c_long", "feature_name": "c_long"},
            ],
        }
    }

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "required": True, "id": "1"},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": "2"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "3"},
    }

    with pytest.raises(UserException):
        spark_util.ingest(get_context(ctx_obj), spark).collect()


def test_ingest_parquet_failed_requirements(
    capsys, spark, write_parquet_file, ctx_obj, get_context
):
    data = [(None, 0.1, None), ("b", 1.0, None), ("c", 1.1, 4)]

    schema = StructType(
        [
            StructField("a_str", StringType()),
            StructField("b_float", FloatType()),
            StructField("c_long", LongType()),
        ]
    )

    path_to_file = write_parquet_file(spark, data, schema)

    ctx_obj["environment"] = {
        "data": {
            "type": "parquet",
            "path": path_to_file,
            "schema": [
                {"column_name": "a_str", "feature_name": "a_str"},
                {"column_name": "b_float", "feature_name": "b_float"},
                {"column_name": "c_long", "feature_name": "c_long"},
            ],
        }
    }

    ctx_obj["raw_features"] = {
        "a_str": {"name": "a_str", "type": "STRING_FEATURE", "values": ["a", "b"], "id": "1"},
        "b_float": {"name": "b_float", "type": "FLOAT_FEATURE", "required": True, "id": "2"},
        "c_long": {"name": "c_long", "type": "INT_FEATURE", "required": False, "id": "3"},
    }

    ctx = get_context(ctx_obj)
    df = spark_util.ingest(ctx, spark)

    validations = spark_util.value_check_data(ctx, df)
    assert validations == {"a_str": [("(a_str IN (a, b))", 1)]}


def test_column_names_to_index():
    sample_feature_input_config = {"b": "b_col", "a": "a_col"}
    actual_list, actual_dict = spark_util.column_names_to_index(sample_feature_input_config)
    assert (["a_col", "b_col"], {"b": 1, "a": 0}) == (actual_list, actual_dict)

    sample_feature_input_config = {"a": "a_col"}

    actual_list, actual_dict = spark_util.column_names_to_index(sample_feature_input_config)
    assert (["a_col"], {"a": 0}) == (actual_list, actual_dict)

    sample_feature_input_config = {"nums": ["a_long", "a_col", "b_col", "b_col"], "a": "a_long"}

    expected_col_list = ["a_col", "a_long", "b_col"]
    expected_feature_input_config = {"nums": [1, 0, 2, 2], "a": 1}
    actual_list, actual_dict = spark_util.column_names_to_index(sample_feature_input_config)

    assert (expected_col_list, expected_feature_input_config) == (actual_list, actual_dict)


def test_run_builtin_aggregators_success(spark, ctx_obj, get_context):
    ctx_obj["aggregators"] = {
        "cortex.sum": {"name": "sum", "namespace": "cortex"},
        "cortex.first": {"name": "first", "namespace": "cortex"},
    }
    ctx_obj["aggregates"] = {
        "sum_a": {
            "name": "sum_a",
            "id": "1",
            "aggregator": "cortex.sum",
            "inputs": {"features": {"col": "a"}},
        },
        "first_a": {
            "id": "2",
            "name": "first_a",
            "aggregator": "cortex.first",
            "inputs": {"features": {"col": "a"}, "args": {"ignorenulls": "some_constant"}},
        },
    }
    aggregate_list = [v for v in ctx_obj["aggregates"].values()]

    ctx = get_context(ctx_obj)
    ctx.store_aggregate_result = MagicMock()
    ctx.populate_args = MagicMock(return_value={"ignorenulls": True})

    data = [Row(a=None), Row(a=1), Row(a=2), Row(a=3)]
    df = spark.createDataFrame(data, StructType([StructField("a", LongType())]))

    spark_util.run_builtin_aggregators(aggregate_list, df, ctx, spark)
    calls = [
        call(6, ctx_obj["aggregates"]["sum_a"]),
        call(1, ctx_obj["aggregates"]["first_a"]),
    ]
    ctx.store_aggregate_result.assert_has_calls(calls, any_order=True)

    ctx.populate_args.assert_called_once_with({"ignorenulls": "some_constant"})


def test_run_builtin_aggregators_error(spark, ctx_obj, get_context):
    ctx_obj["aggregators"] = {"cortex.first": {"name": "first", "namespace": "cortex"}}
    ctx_obj["aggregates"] = {
        "first_a": {
            "name": "first_a",
            "aggregator": "cortex.first",
            "inputs": {
                "features": {"col": "a"},
                "args": {"ignoreNulls": "some_constant"},  # supposed to be ignorenulls
            },
            "id": "1",
        }
    }

    aggregate_list = [v for v in ctx_obj["aggregates"].values()]

    ctx = get_context(ctx_obj)
    ctx.store_aggregate_result = MagicMock()
    ctx.populate_args = MagicMock(return_value={"ignoreNulls": True})

    data = [Row(a=None), Row(a=1), Row(a=2), Row(a=3)]
    df = spark.createDataFrame(data, StructType([StructField("a", LongType())]))
    with pytest.raises(Exception):
        spark_util.run_builtin_aggregators(aggregate_list, df, ctx, spark)

    ctx.store_aggregate_result.assert_not_called()
    ctx.populate_args.assert_called_once_with({"ignoreNulls": "some_constant"})
