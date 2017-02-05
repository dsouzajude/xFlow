import json
import logging
import functools, traceback

import jsonschema
from jsonschema import validate
import bottle, sys; bottle._stderr = sys.stdout.write
from bottle import error, request, Bottle, response, install

import core


class ApiException(Exception):
    code = 400


class BadRequest(ApiException):
    pass


class NotFoundException(ApiException):
    code = 404


class JsonSchemaValidator(object):
    def __init__(self, schema):
        self.schema = schema

    def validate(self, obj):
        validate(obj, schema=self.schema)



log = logging.getLogger(__name__)


# Json Schema Validators
########################
publish_schema = JsonSchemaValidator({
    '$schema': 'http://json-schema.org/schema#',
    'definitions': {
        'event': {
            'type': 'object',
            'properties': {
                'execution_id': {
                    'type': 'string'
                }
            },
            'required': ['execution_id']
        },
    },
    'type': 'object',
    'properties': {
        'stream': {'type': 'string'},
        'event': {'$ref': '#/definitions/event'}
    },
    'required': ['stream', 'event']
})


def create_app(engine):
    app = Bottle()

    @app.error()
    @app.error(404)
    def handle_error(error):
        if issubclass(type(error.exception), ApiException):
            response.status = error.exception.code
        else:
            response.status = error.status_code
        response.set_header('Content-type', 'application/json')
        resp = {
            'type': type(error.exception).__name__,
            'message': repr(error.exception) if error.exception else '',
            'traceback': error.traceback,
            'status_code': response.status
        }
        log.error('Exception, type=%s, message=%s, status_code=%s, traceback=%s'\
                    % (resp['type'], resp['message'], resp['status_code'], resp['traceback']))
        return '%s %s' % (resp['status_code'], resp['message'])

    @app.route('/ping', method=['GET'])
    def ping():
        return {'name': 'xFlow', 'version': '0.1' }

    @app.route('/publish', method=['POST'])
    def publish():
        data = json.loads(request.body.read())
        try:
            publish_schema.validate(data)
        except jsonschema.ValidationError as err:
            raise BadRequest(err)

        stream = data['stream']
        event = json.dumps(data['event'])
        try:
            engine.publish(stream, event)
        except core.KinesisStreamDoesNotExist as ex:
            raise NotFoundException(str(ex))
        return {}

    @app.route('/track/workflows/<workflow_id>/executions/<execution_id>', method=['GET'])
    def track(workflow_id, execution_id):
        try:
            tracking_info = engine.track(workflow_id, execution_id)
            return tracking_info
        except (core.CloudWatchStreamDoesNotExist,
                core.WorkflowDoesNotExist,
                core.CloudWatchLogDoesNotExist) as ex:
            raise NotFoundException(str(ex))
        raise Exception("Something went wrong!")

    return app
