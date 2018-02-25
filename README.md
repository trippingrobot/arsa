# Arsa Python SDK

Welcome to the Arsa Python SDK. This sdk will help to deploy your api to Arsa by providing
a wrapper around your Swagger file and simple conventions to point your endpoints
to your application logic.

## Quick Start Guide

Install the sdk using pip like so...

```
pip install arsa-sdk
```

Create a Swagger 2.0 definition file called `swagger.yaml` describing your api endpoints...

```yaml
swagger: "2.0"
info:
  description: Sample Arsa API
  version: "0.0.1"
  title: "Sample Arsa"
  contact:
    email: "sample@api.io"
  license:
    name: "Apache 2.0"
    url: "http://www.apache.org/licenses/LICENSE-2.0.html"
host: "sample.api.io"
basePath: "/v1"
paths:
  /users:
    get:
      summary: "List the available users"
      description: ""
      operationId: "users.list"
      produces:
      - "application/json"
      responses:
        200:
          description: "successful operation"
          schema:
            type: "array"
            items:
              $ref: "#/definitions/User"
        405:
          description: "Invalid input"
definitions:
  User:
    type: "object"
    properties:
      id:
        type: "integer"
        format: "int64"
        readOnly: true
      name:
        type: "string"
      email:
        type: "string"
```

Configure your project for Arsa.

```
arsa config
```

Create a `handler.py` file to handle your API routes

```python
from arsa-sdk import Router

@Router.route("users.list")
def list_users():
    """ Get users """
    return []
```

Deploy your API to arsa.io

```
arsa deploy
```
