#!/usr/bin/env python3
import os
import tornado.ioloop
import tornado.web
import tornado.log
import requests


from jinja2 import \
    Environment, PackageLoader, select_autoescape

ENV = Environment(
    loader=PackageLoader('dashboard', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
PORT = int(os.environ.get('PORT', '1337'))


class TemplateHandler(tornado.web.RequestHandler):
    def render_template(self, tpl, context):
        template = ENV.get_template(tpl)
        self.write(template.render(**context))


class LoginHandler(tornado.web.RequestHandler, tornado.auth.GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        # This portion gets triggered second apon a person's first login
        # The authorization `code` in the URL that was returned from Google
        # allows for this statement to be true
        # Example URL:
        # http://example.com/login?code=4/GdQlpUVhfTvV6tReFLG6q9czdTd32NWn3wzC90dwlTc
        if self.get_argument('code', False):
            # Exchanges the authorization `code` for an access token
            access = yield self.get_authenticated_user(
                redirect_uri='http://localhost:1337/login',
                code=self.get_argument('code'))
            # After obtaining an access token, that token can be used to gain access to user info
            user = yield self.oauth2_request(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                access_token=access["access_token"])

            print(user)
            # Retrieve user information
            email = user["email"]
            fname = user["given_name"]
            lname = user["family_name"]
            picture = user["picture"]
            # Check if user already exists in Users table

            # If user does not exist, insert user into Users table


            # Signs and timestamps a cookie so it cannot be forged
            # User will not have to login again as long as cookie is not tampered with or deleted
            self.set_secure_cookie('crypto_user', user['email'])
            self.redirect('/')
            return

        elif self.get_secure_cookie('crypto_user'):
            self.redirect('/')
            return

        # This portion actually gets triggered first apon a person's first login
        # An authorization `code` is returned from Google
        # A redirect is made to this same Loginhandler with that authorization code
        else:
            yield self.authorize_redirect(
                redirect_uri="http://localhost:1337/login",
                client_id=self.settings['google_oauth']['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})


class MainHandler(TemplateHandler):
    def get(self):
        self.render_template("index.html", {})



    def post(self):
        url = "https://bittrex.com/api/v1.1/public/getmarketsummary"
        coin = self.get_body_argument('ticker_symbol')
        querystring = {"market": "btc-" + coin}

        response = requests.post(url, params=querystring)

        print(response.json())
        self.render_template("index.html", {'data': response.json()})

class ParsedDataHandler(TemplateHandler):
        def get(self, page):
                self.set_header(
                  'Cache-Control',
                  'no-store, no-cache, must-revalidate, max-age=0')
                self.render_template('data_parser.html', {})

        def orderbook(self):
            url = "https://bittrex.com/api/v1.1/public/getorderbook"

            querystring = {"market": "BTC-LTC", "type": "both"}

            headers = {
                'cache-control': "no-cache",
                'postman-token': "1700863e-c007-79df-6a9b-bc985f2ff94d"
            }

            response = requests.request("GET", url, headers=headers, params=querystring)

            self.render_template('data_parser.html', {})

settings = {
    "autoreload": True,
    "google_oauth": {"key": os.environ["CLIENT_ID"], "secret": os.environ["CLIENT_SECRET"]},
    "cookie_secret": os.environ["COOKIE_SECRET"]}


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/data_parser(.*)", ParsedDataHandler),
        (r"/static/(.*)",
         tornado.web.StaticFileHandler, {'path': 'static'}),
    ], **settings)

if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    app = make_app()
    app.listen(PORT, print('Creating magic on port: ' + str(PORT)))
    tornado.ioloop.IOLoop.current().start()
