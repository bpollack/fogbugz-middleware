import re
import sys
import urllib
import urllib2
from django.conf import settings
from django.http import Http404

class FogBugzMiddleware(object):
    """Report Django exceptions to FogBugz

    FogBugzMiddleware intercepts exceptions thrown from within Django
    and forwards them to FogBugz' ScoutSubmit form.  It will then
    allow processing to continue--meaning that if you have Django
    set to send an email on error, it will continue to do so."""
    
    def process_response(self, request, response):
        if response.status_code == 404:
            if settings.FOGBUGZ_REPORT_BROKEN_LINKS:
                domain = request.get_host()
                referer = request.META.get('HTTP_REFERER', None)
                path = request.get_full_path()
                is_internal = _is_internal_request(domain, referer)
                if referer and not _is_ignorable_404(path) and is_internal:
                    ua = request.META.get('HTTP_USER_AGENT', '<none>')
                    ip = request.META.get('REMOTE_ADDR', '<none>')
                    
                    bug = {'ScoutUserName': settings.FOGBUGZ_USERNAME,
                           'ScoutProject': settings.FOGBUGZ_PROJECT,
                           'ScoutArea': settings.FOGBUGZ_AREA,
                           'Description': 'Broken %slink %s on %s' % ((is_internal and 'INTERNAL ' or ''), request.path, domain),
                           'Extra': 'Referrer: %s\nRequested URL: %s\nUser agent:%s\nIP address: %s\n' \
                               % (referer, request.get_full_path(), ua, ip)}
                    
                    try:
                        urllib2.urlopen(settings.FOGBUGZ_URL, urllib.urlencode(bug))
                    except:
                        pass
        return response
    
    def process_exception(self, request, exception):
        # Do not file 404 errors in FogBugz
        if isinstance(exception, Http404):
            return

        bug = {}
        bug["ScoutUserName"] = settings.FOGBUGZ_USERNAME
        bug["ScoutProject"] = settings.FOGBUGZ_PROJECT
        bug["ScoutArea"] = settings.FOGBUGZ_AREA
        bug["Description"] = '%s error: %s at %s' % ((request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'Internal' or 'External'), exception.__class__.__name__, request.path)
        
        try:
            request_repr = repr(request)
        except:
            request_repr = 'Request repr() unavailable'
        bug["Extra"] = '%s\n\n%s' % (_get_traceback(sys.exc_info()), request_repr)
        
        try:
            urllib2.urlopen(settings.FOGBUGZ_URL, urllib.urlencode(bug))
        except:
            # Don't throw an exception within the error handler!  Bad!
            pass

def _get_traceback(exc_info):
    """Helper function to return the traceback as a string"""
    import traceback
    return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))

def _is_internal_request(domain, referer):
    """Returns true if the referring URL is the same domain as the current
    request."""
    return referer is not None and re.match("^https?://%s/" % re.escape(domain), referer)

def _is_ignorable_404(uri):
    """
    Returns True if a 404 at the given URL *shouldn't* notify the site managers.
    """
    for start in settings.IGNORABLE_404_STARTS:
        if uri.startswith(start):
            return True
    for end in settings.IGNORABLE_404_ENDS:
        if uri.endswith(end):
            return True
    return False
