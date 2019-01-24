# Config

These environment variables can be modified and exported before running `cortex.sh` commands. Alternatively, `cortex.sh` will automatically look for a `config.sh` file or a different file if you use `cortex.sh --config [path]`.

[comment]: <> (CORTEX_VERSION_MINOR)

```bash
# AWS credentials
export AWS_ACCESS_KEY_ID="***"
export AWS_SECRET_ACCESS_KEY="***"

# The name of the CloudWatch log group Cortex will use
export CORTEX_LOG_GROUP="cortex" # (default)

# The name of the S3 bucket Cortex will use
export CORTEX_BUCKET="cortex-[RANDOM_ID]" # (default)

# The AWS region Cortex will use
export CORTEX_REGION="us-west-2" # (default)

# The name of the Kubernetes namespace Cortex will use
export CORTEX_NAMESPACE="cortex" # (default)

# Image paths
export CORTEX_IMAGE_ARGO_CONTROLLER="cortexlabs/argo-controller:0.1" # (default)
export CORTEX_IMAGE_ARGO_EXECUTOR="cortexlabs/argo-executor:0.1" # (default)
export CORTEX_IMAGE_FLUENTD="cortexlabs/fluentd:0.1" # (default)
export CORTEX_IMAGE_NGINX_BACKEND="cortexlabs/nginx-backend:0.1" # (default)
export CORTEX_IMAGE_NGINX_CONTROLLER="cortexlabs/nginx-controller:0.1" # (default)
export CORTEX_IMAGE_OPERATOR="cortexlabs/operator:0.1" # (default)
export CORTEX_IMAGE_SPARK="cortexlabs/spark:0.1" # (default)
export CORTEX_IMAGE_SPARK_OPERATOR="cortexlabs/spark-operator:0.1" # (default)
export CORTEX_IMAGE_TF_SERVE="cortexlabs/tf-serve:0.1" # (default)
export CORTEX_IMAGE_TF_TRAIN="cortexlabs/tf-train:0.1" # (default)
export CORTEX_IMAGE_TF_API="cortexlabs/tf-api:0.1" # (default)
```
