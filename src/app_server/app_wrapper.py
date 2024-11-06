from werkzeug.wrappers import Request, Response
class AppWrapper:
    """simple wrapping app"""
    @staticmethod
    def wsgi_app(environ, start_response):
        request = Request(environ)
        response = Response(f'Path not found or invalid: {request.path}',
                            status=404)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)
