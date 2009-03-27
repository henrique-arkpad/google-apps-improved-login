from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import gdata.alt.appengine
import os
import gdata.apps.service
import urllib
import settings
import utils
from google.appengine.ext.webapp import template

class ShowLogin(webapp.RequestHandler):
  def get(self):
    domain = settings.GAPPS_DOMAIN
    if self.request.get('SAMLRequest') == '':
      self.redirect('https://mail.google.com/a/' + domain)
      return
    requestdata = utils.unpackSAMLRequest(self, self.request.get('SAMLRequest'))
    age = requestdata['requestage']
    if (age < 0) or (age > 590): # is our SAMLRequest old or invalid?
      self.redirect('https://mail.google.com/a/' + domain)
    template_values = {
    #we want to refresh 10 sec before SAMLRequest expires
      'refresh': int(590 - age),
      'samlrequest': self.request.get('SAMLRequest'),
      'relaystate': self.request.get('RelayState'),
      'error': self.request.get('Error'),
      'domain': domain,
      'appspot_domain': os.environ['APPLICATION_ID']+'.appspot.com'
      }
    path = os.path.join(os.path.dirname(__file__), 'templates')
    path = os.path.join(path, 'login.html')
    self.response.out.write(template.render(path, template_values))

class DoLogin(webapp.RequestHandler):
  def post(self):
    becomeattempt = False
    loginvalue = str(self.request.get('username'))
    if loginvalue.find('+') != -1:
      username = loginvalue[0:(loginvalue.find('+'))]
      loginuser = loginvalue[(loginvalue.find('+') + 1):]
      becomeattempt = True
    else:
      username = loginvalue
    password = str(self.request.get('password'))
    domain = settings.GAPPS_DOMAIN
    apps = gdata.apps.service.AppsService(email=username+'@'+domain, domain=domain, password=password)
    gdata.alt.appengine.run_on_appengine(apps, store_tokens=True, single_user_mode=True)
    try:
      apps.ProgrammaticLogin()
    except gdata.service.BadAuthentication:
      self.redirect('/?SAMLRequest='+urllib.quote(self.request.get('SAMLRequest'))+'&RelayState='+urllib.quote(self.request.get('RelayState'))+'&Error=Unknown%20Username%20or%20Password')
    except gdata.service.CaptchaRequired:
      self.redirect('/?SAMLRequest='+urllib.quote(self.request.get('SAMLRequest'))+'&RelayState='+urllib.quote(self.request.get('RelayState'))+'&Error=Your%20account%20is%20locked.%20%3Ca%20href%3D%22https%3A//www.google.com/a/'+domain+'/UnlockCaptcha%22%3EClick%20here%20to%20unlock%20it.%3C/a%3E')
    if becomeattempt:
      if utils.userCanBecomeUser(apps, username, loginuser):
        username = loginuser
      else:
        self.redirect('/?SAMLRequest='+urllib.quote(self.request.get('SAMLRequest'))+'&RelayState='+urllib.quote(self.request.get('RelayState'))+'&Error=Unknown%20Username%20or%20Password')
    self.response.out.write(utils.createAutoPostResponse(self, self.request.get('SAMLRequest'), username))

class Password(webapp.RequestHandler):
  def get(self):
    self.response.out.write(open(templates/password.html).read())
  
      
application = webapp.WSGIApplication(
                                     [('/dologin', DoLogin),
                                      ('/', ShowLogin),
                                      ('/password', Password)],
                                     debug=False)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
