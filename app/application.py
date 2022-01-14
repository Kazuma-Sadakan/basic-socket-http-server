import os, sys, json
from server import Server

class Application(object):
    url_map = {}
    environ = None
    start_response = None

    def __init__(self, name):
        self.name = name 

    def wsgi_app(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response 
        return self

    def __call__(self, f):
        f()

    def get_routes(self):
        return self.url_map

    def run(self, host = "localhost" , port = 8000):
        server = Server((host, port))
        server.set_app(self.wsgi_app)
        server.server_forever()
        
    def route(self, path, method = ["GET"]):
        def wrap(func):
            self.url_map[path] = [func, method]
        return wrap

    def request(self, key):
        params  = json.loads(self.environ.get("body", None))
        return params[key]

    def handle(self):
        try:
            # set defautl status and content_type
            status = "200 OK"
            content_type = "text/html; charset=utf-8"
            url = self.environ.get("PATH_INFO", "/")
            if self.environ.get("REQUEST_METHOD", "GET") in self.url_map[url][1]:
                func = self.url_map[url][0]
                print(func)
                func()

            if url.endswith(".css"):
                self.url = "./static/css/style.css"
                content_type = "text/css"
                
            if url.endswith(".js"):
                self.url = "./static/js/main.js" 
                content_type = "text/application" 


        except Exception as e:
            print(e)
            status = "400 Bad Request"
            url = "./templates/error.html"

        finally:
            return content_type, status

    def render_template(self, url):
        self.url = f"./templates/{url}"
        return self.url
            
    def __iter__(self):
        response_headers = [("Content-type", "text/html; charset=utf-8")]
        ctype, status = self.handle()
        content_length = os.path.getsize(self.url)
        response_body = open(self.url, mode="rb").read(content_length)
        # response_body = json.dumps(body).encode("utf-8")
        response_headers.append(("Content-Length", content_length))
        # method = self.environ.get("REQUEST_METHOD", "GET")
        # query = self.environ.get("QUERY_STRING", "")
        # content_length = self.environ.get("CONTENT_LENGTH", 0)
        # if method == "POST":
        #     request_body = self.environ.get("wsgi.input").read(int(content_length)) #string
        self.start_response(status, response_headers)
        yield response_body #utf-8


