from application import Application
py = Application(__name__)

@py.route('/', method=["GET"])
def home():
    return py.render_template("home.html")


@py.route('/sign_up', method=["GET", "POST"])
def signup():
    return py.render_template("sign_up.html")

if __name__ == "__main__":
    py.run()
