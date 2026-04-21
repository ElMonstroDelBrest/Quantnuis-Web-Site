# API module
# Lazy import: api/main.py requires mangum (Lambda-only dependency)
# On EC2, only api.ec2_api.main is used directly
import os as _os

if _os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    from .main import app, handler
    __all__ = ["app", "handler"]
else:
    __all__ = []
