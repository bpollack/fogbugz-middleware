import sys
import urllib, urllib2
from django.conf import settings

class FogBugzMiddleware(object):
    """Report Django exceptions to FogBugz

    FogBugzMiddleware intercepts exceptions thrown from within Django
    and forwards them to FogBugz' ScoutSubmit form.  It will then
    allow processing to continue--meaning that if you have Django
    set to send an email on error, it will continue to do so."""
    
    def process_exception(self, request, exception):
        bug = {}
        bug["ScoutUserName"] = settings.FOGBUGZ_USERNAME
        bug["ScoutProject"] = settings.FOGBUGZ_PROJECT
        bug["ScoutArea"] = settings.FOGBUGZ_AREA
        bug["Description"] = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'), request.path)
        
        try:
            request_repr = repr(request)
        except:
            request_repr = 'Request repr() unavailable'
        bug["Extra"] = '%s\n\n%s' % (self._get_traceback(sys.exc_info()), request_repr)
        
        try:
            urllib2.urlopen(settings.FOGBUGZ_URL, urllib.urlencode(bug))
        except:
            # Don't throw an exception within the error handler!  Bad!
            pass

    def _get_traceback(self, exc_info):
        """Helper function to return the traceback as a string"""
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
