# Introduction #

In order for OAuth to work, you need to register the domain
of your App Engine app with Google. This is necessary because users will be entrusting Moveable Weather with their Latitude data. Their are several ways to accomplish this registration, but we outline one technique below.

# Details #

Perform the following steps.

  1. Go to https://www.google.com/accounts/ManageDomains
  1. Choose the "upload an html file" method
    * Google will offer you file with a name like `googlead47db9711b4789c.html` for download
    * in app/my\_globals.py, use this file as the value of `GOOGLE_VERIFY_FILE`
    * From the `app` folder, issue the command:
```
  appcfg.py update .
```
      * Now visit http://MY_APP.appspot.com/GOOGLE_VERIFY_FILE (Substituting your values)
      * Press the Verify button.
      * Google gives you back the consumser secret, something like:
> > > > `wiExtkNLdsYsKwiExtkNLdsYsK`
      * In `app/my_globals.py` use this as the value of `MY_OAUTHCONSUMER_SECRET`
      * When Google  ask you for the target url path prefix, use
> > > > /