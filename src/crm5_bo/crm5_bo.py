'''CRM 5 Backoffice APIs.

'''

# System imports
import base64
import functools
import http.client
import json
import logging
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

# External imports
import requests

http_logger = logging.getLogger('httplogger')
logger = logging.getLogger(__name__)

class CRM5APIError(RuntimeError):
    """Raised when the CRM API returns a non-2xx HTTP response."""

def _deprecated(replacement: str):
    """Mark a method as deprecated in favour of `replacement`.

    Each call emits a `DeprecationWarning` (visible under `python -W`,
    pytest, etc.) and a matching `logger.warning` call (visible in
    application logs even when warnings filters are left at their default),
    identifying the replacement to migrate to. Once your logs stop showing
    calls to a given deprecated name, it's safe to delete that alias.

    Args:
        replacement (str): Name of the method to use instead.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            message = (
                f"{type(self).__name__}.{func.__name__}() is deprecated "
                f"and will be removed in a future release, use "
                f".{replacement}() instead."
            )
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            logger.warning(message)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

class CRM5BackofficeAdmin:
    '''CRM.com BackOffice Admin API.

    API Docs (current version v2):
    https://crmcom.stoplight.io/docs/stoplight-api-doc/
    '''
    _backoffice_url = '/backoffice/v2'


    def __init__(self, crm_domain: str) -> None:
        """Constructor.

        Args:
            crm_domain (str): CRM tenant domain (e.g. 'app.crm.com'), used to
                build the base URL for all API requests.
        """
        self._crm_domain            = crm_domain
        self._username              = None
        self._password              = None
        self._api_key               = None
        self._secret_key            = None
        self._access_token          = None
        self._refresh_token         = None
        self._debug_state           = False
        self._timeout               = 60
        self._default_page_size     = 100
        self._default_thread_count  = 6
        self._expiration_date       = None
        self._organization_mod      = None
        self._lockout_date          = None
        self._password_expired      = None

    def fields_to_dict(self, custom_fields:list[dict[str,str]]):
        '''Fields to dictionary.

        Custom fields from CRM come in the form:
        'custom_fields': [
            {'key': 'overdue_invoice_amount', 'value': '<value>'},
            {'key': 'custom_emails',          'value': '<value> '},
            {'key': 'email_notes',            'value': '<value>'},
            {'key': 'credit_limit_v4',        'value': '5232130.0'},
            {'key': 'phone_notes',            'value': 'Main'},
            {'key': 'number_of_days_passed',  'value': '5'},
            {'key': 'custom_phones',          'value': 'CUSTOM3-kjfshkjhashdsa'},
            {'key': 'account_number',         'value': '982743749382739'}
        ],
        which can be a pain to work with.

        This function turns that form into a single dictionary of the form:
        'custom_fields_dict': {
            'overdue_invoice_amount': '<value>',
            'custom_emails': '<value> ',
            'email_notes': '<value>',
            'credit_limit_v4': '5232130.0',
            'phone_notes': 'Main',
            'number_of_days_passed': '5',
            'custom_phones': 'CUSTOM3-kjfshkjhashdsa',
            'account_number': '982743749382739'
        }
        '''
        return {v['key']:v['value'] for v in custom_fields}

    def debug(self, debug_state: bool | None = None) -> bool:
        """Get / Set debug state.

        if a debug_state is passed then set the debug state and logging
        parameters. If None is set then simply return the value.

        Warning:
            Enabling debug logs the raw HTTP request/response, including the
            `authorization`/`api_key` headers and the login password. Do not
            enable this in shared terminals or environments where logs are
            persisted or forwarded.

        Args:
            debug_state (bool, optional): True to enable verbose HTTP debug
                logging, False to disable it. Defaults to None, which leaves
                the current state unchanged.

        Returns:
            bool: The current debug state.
        """
        if debug_state is None:
            return self._debug_state

        self._debug_state = debug_state
        if self._debug_state:
            http.client.HTTPConnection.debuglevel = 2
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            http.client.HTTPConnection.debuglevel = 0
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.ERROR)
            requests_log.propagate = True
        return self._debug_state

    def _buid_url(self, relative_url: str) -> str:
        """Build the full URL for making a request.

        Args:
            relative_url (str): API path relative to the backoffice base
                path, e.g. '/contacts'.

        Returns:
            str: The full HTTPS URL for the request.
        """
        base_url = f"{self._backoffice_url}{relative_url}"

        return urllib.parse.urljoin(f"https://{self._crm_domain}", base_url)

    def _auth_headers(self) -> dict:
        """Build the authorization headers used by authenticated API calls.

        Returns:
            dict: Headers containing the access token and API secret key.
        """
        return {
            'authorization': self._access_token,
            'api_key':       self._secret_key,
        }

    def _make_request(self, method: str, url: str, json_data: dict | None = None, headers: dict | None = None,
                      get_params: dict | None = None) -> requests.Response:
        """Make a request to the CRM api.

        Args:
            method (str): HTTP method to use.
            url (str): URL to request, relative to the backoffice base path.
            json_data (dict, optional): JSON data to post. Defaults to None.
            headers (dict, optional): Headers to use for request. Defaults to None.
            get_params (dict, optional): If this is a HTTP GET the URL query parameters. Defaults to None.

        Raises:
            CRM5APIError: If the response status code is not in the 2xx range.

        Returns:
            requests.Response: The raw HTTP response.
        """
        req_params = {}

        if get_params is not None:
            req_params['params'] = get_params

        req = requests.request(
            method,
            self._buid_url(url),
            json=json_data,
            headers=headers,
            timeout=self._timeout,
            **req_params
        )
        if self._debug_state:
            logger.debug(f"Return body: {req.text}")

        if not (200 <= req.status_code < 300):
            # Error we need to handle
            if self._debug_state:
                logger.error(f"Recv error code: {req.status_code}")
                logger.error(f"Body: {req.text}")
            raise CRM5APIError(f"HTTP Error '{req.status_code}' -> {req.text}")

        return req

    def _fetch_page(self, method: str, url: str, json_data: dict | None = None, headers: dict | None = None,
                    get_params: dict | None = None, page_num: int | None = None) -> dict:
        """Fetch a single page of a query.

        Args:
            method (str): HTTP method to use.
            url (str): URL to request, relative to the backoffice base path.
            json_data (dict, optional): JSON data to post. Defaults to None.
            headers (dict, optional): Headers to use for request. Defaults to None.
            get_params (dict, optional): Query string parameters. Defaults to None.
            page_num (int, optional): Page number to fetch; sets the 'page'
                query parameter when given. Defaults to None.

        Returns:
            dict: The page's response body, with 'content' and 'paging' keys.
        """
        if get_params is None:
            get_params = {}
        else:
            get_params = dict(get_params)
        if 'size' not in get_params:
            get_params['size'] = self._default_page_size
        if page_num is not None:
            get_params['page'] = page_num

        req = self._make_request(
            method,
            url,
            json_data,
            headers,
            get_params,
        )

        req_data = req.json()

        if req_data['content'] is None:
            raise CRM5APIError("Call returned no content, call not implemented")

        # Seems total isn't set under all cirmstances.
        if req_data['paging']['total'] is None:
            req_data['paging']['total'] = req_data['paging']['size']
        return req_data

    def _fetch_all(self, method: str, url: str, json_data: dict | None = None, headers: dict | None = None, get_params: dict | None = None) -> dict:
        """Make iterative requests to fetch the complete result set.

        Args:
            method (str): HTTP method to use.
            url (str): URL to request, relative to the backoffice base path.
            json_data (dict, optional): JSON data to post. Defaults to None.
            headers (dict, optional): Headers to use for request. Defaults to None.
            get_params (dict, optional): Query string / search parameters. Defaults to None.

        Returns:
            dict: The combined response, with 'content' extended across all
                pages and 'paging' reflecting the full result set.
        """
        logger.debug(f"Fetch all {method} -> {url}")
        if get_params is None:
            get_params = {}
        else:
            get_params = dict(get_params)
        if 'size' not in get_params:
            get_params['size'] = self._default_page_size

        req_data = self._fetch_page(
            method=method,
            url=url,
            json_data=json_data,
            headers=headers,
            get_params=get_params,
        )

        page_size = int(req_data['paging']['size'])

        logger.debug(f"First page data: {req_data['paging']}")
        if req_data['paging']['has_more'] is False:
            return req_data

        if 'size' not in get_params or get_params['size'] != page_size:
            get_params['size'] = page_size

        curr_page = 2
        while True:
            logger.debug(f"Fetching page: {curr_page}")
            curr_page_req_data = self._fetch_page(
                method=method,
                url=url,
                json_data=json_data,
                headers=headers,
                get_params=get_params,
                page_num=curr_page,
            )
            logger.debug(f"Page {curr_page} - paging {curr_page_req_data['paging']}")
            req_data['content'].extend(curr_page_req_data['content'])
            if curr_page_req_data['paging']['has_more'] is False:
                req_data['paging']['has_more'] = curr_page_req_data['paging']['has_more']
                break

            curr_page += 1

        req_data['paging']['pages'] = curr_page
        req_data['paging']['total'] = len(req_data['content'])

        return req_data

    def _fetch_all_parallel_search_max(self, pages_dict: dict, method: str,
            url: str, json_data: dict | None = None, headers: dict | None = None, get_params: dict | None = None) -> tuple[int, int]:
        """Find the last page of a paginated result set.

        Uses an exponential probe (page 1, 10, 100, ...) to find an upper
        bound, then binary searches between the last two probed pages to
        find the exact last page. Every page fetched along the way is
        cached into `pages_dict` so the caller doesn't need to re-fetch it.

        Args:
            pages_dict (dict): Cache of already-fetched pages, keyed by page
                number; populated with every page fetched during the search.
            method (str): HTTP method to use.
            url (str): URL to request, relative to the backoffice base path.
            json_data (dict, optional): JSON data to post. Defaults to None.
            headers (dict, optional): Headers to use for request. Defaults to None.
            get_params (dict, optional): Query string parameters shared by
                every page request. Defaults to None.

        Returns:
            tuple[int, int]: The last page number and that page's record count.
        """
        page = 1
        multiplier = 10


        for _ in range(10):
            logger.debug(f"Testing page m: {page}")
            pages_dict[page] = self._fetch_page(
                method=method,
                url=url,
                json_data=json_data,
                headers=headers,
                get_params=get_params,
                page_num=page,
            )
            logger.debug(f"Page {page} - paging {pages_dict[page]['paging']}")

            if pages_dict[page]['paging']['has_more'] is False:
                break

            page *= multiplier

        # page is an upper bound, page /= multiplier is the lower
        # Binary search to the actual last page
        if pages_dict[page]['paging']['size'] != 0:
            # This actually is the last page
            return page, pages_dict[page]['paging']['size']
        else:
            # Do the divide and conquer strategy
            lower_bound = int(page / multiplier)
            upper_bound = page

            page = int(upper_bound // 2)

            while lower_bound <= upper_bound:
                logger.debug(f"Testing page b: {page} : {lower_bound} => {upper_bound}")
                pages_dict[page] = self._fetch_page(
                    method=method,
                    url=url,
                    json_data=json_data,
                    headers=headers,
                    get_params=get_params,
                    page_num=page,
                )
                logger.debug(f"Page {page} - paging {pages_dict[page]['paging']}")

                if pages_dict[page]['paging']['has_more'] is False:
                    if pages_dict[page]['paging']['size'] != 0:
                        return page,pages_dict[page]['paging']['size']
                    else:
                        # We are too high
                        upper_bound = page - 1
                else: # has_more is True
                    # We are too low
                    lower_bound = page + 1

                page = int((lower_bound + upper_bound) // 2)

        return -1,-1

    def _fetch_all_parallel(self, method: str, url: str, json_data: dict | None = None,
                            headers: dict | None = None, get_params: dict | None = None, thread_count: int | None = None
                            ) -> dict:
        """Make parallel requests to fetch the complete result set.

        Args:
            method (str): HTTP method to use.
            url (str): URL to request, relative to the backoffice base path.
            json_data (dict, optional): JSON data to post. Defaults to None.
            headers (dict, optional): Headers to use for request. Defaults to None.
            get_params (dict, optional): Query string / search parameters. Defaults to None.
            thread_count (int, optional): Number fo parallel requests. Defaults
                                          to None which then becomes
                                          _default_thread_count.

        Returns:
            dict: The combined response across all pages, with 'content'
                merged and 'paging' summarizing the full result set.
        """
        logger.debug(f"Fetch all parallel {method} -> {url}")
        if get_params is None:
            get_params = {}
        else:
            get_params = dict(get_params)
        if 'size' not in get_params:
            get_params['size'] = self._default_page_size
        if thread_count is None:
            thread_count = self._default_thread_count


        # Blank result set
        req_data = { 'content': [], 'paging': { 'pages': 0, 'total': 0 }}

        # Start search for max page
        pages_dict = {}
        max_page,last_page_size = self._fetch_all_parallel_search_max(
            pages_dict, method, url, json_data, headers, get_params,
        )

        logger.debug(f'Max page: {max_page} of size {last_page_size}')

        # Clean pages_dict of all empty pages
        pages_to_del = list(filter(lambda x: x > max_page, pages_dict.keys()))
        for to_del in pages_to_del:
            del pages_dict[to_del]


        # Now paralell request the rest of the pages
        def _fetch_page(page_id: int) -> dict:
            result = self._fetch_page(
                method=method,
                url=url,
                json_data=json_data,
                headers=headers,
                get_params=get_params,
                page_num=page_id,
            )
            return page_id, result

        fetched_pages = pages_dict.keys()
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_url = {
                executor.submit(_fetch_page, page_id=page_id): page_id for page_id in filter(
                    # Filter out pages we already have
                    # We are fetching all from 1 to max_page
                    lambda x: x not in fetched_pages, range(1, max_page)
                )
            }

            for future in as_completed(future_to_url):
                page_id, result = future.result()
                pages_dict[page_id] = result

        # We should now have pages_dict fully populated
        for curr_page_data in pages_dict.values():
            req_data['content'].extend(curr_page_data['content'])

        req_data['paging']['pages'] = max_page
        req_data['paging']['total'] = ((max_page - 1) * get_params['size']) + last_page_size

        return req_data


    def login(self, username: str, password: str, api_key: str, secret_key: str) -> bool:
        """Authenticate user.

        Docs:
        https://speca.io/CRM/backoffice-admin#adminusers-authenticate

        Args:
            username (str): CRM username.
            password (str): CRM password.
            api_key (str):  CRM API key.
            secret_key (str): CRM secret key.

        Returns:
            bool: True if login was successful, False if not.
        """
        self._username = username
        self._password = password
        self._api_key = api_key
        self._secret_key = secret_key

        req = self._make_request(
            'POST',
            '/users/authenticate',
            json_data={
                'provider': "EMAIL",
                'username': self._username,
                'password': self._password,
            },
            headers={
                'api_key': self._api_key,
            },
        )
        auth_data = req.json()

        self._access_token = auth_data['access_token']
        self._refresh_token = auth_data['refresh_token']
        self._expiration_date = auth_data['expiration_date']
        self._organization_mod = auth_data['mode']
        self._lockout_date = auth_data['lockout_date']
        self._password_expired = auth_data['password_expired']

        return True

    def _current_user_id(self) -> str:
        """Get the id of the currently logged in user.

        The `/users/authenticate` response does not include the user's id
        directly, but it is carried as the `sub` claim of the access token
        (a JWT). We only ever read our own token here, so the payload is
        decoded without verifying its signature.

        Returns:
            str: The current user's id (GUID).
        """
        payload_segment = self._access_token.split('.')[1]
        padding = '=' * (-len(payload_segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding))

        return payload['sub']

    def logout(self) -> None:
        """Logout of API.

        Terminates the current user's session, invalidating the access and
        refresh tokens.

        Docs:
        https://speca.io/CRM/backoffice-admin#sign-out-user
        """
        user_id = self._current_user_id()

        self._make_request(
            'POST',
            f'/users/{user_id}/sign_out',
            headers=self._auth_headers(),
        )

        self._access_token = None
        self._refresh_token = None

    def dump_auth(self,) -> dict:
        """Dump the authentication data for cache.

        Warning:
            The returned dict includes the plaintext username and password
            alongside the tokens. If the caller persists this to disk or any
            other store, that store becomes a plaintext credential store and
            must be secured (e.g. restrictive file permissions, encryption
            at rest) accordingly.

        Returns:
            dict: Username, password, API/secret keys, and token/session
                state, suitable for passing to `load_auth` later.
        """
        return {
            'username': self._username,
            'password': self._password,
            'api_key': self._api_key,
            'secret_key': self._secret_key,
            'access_token': self._access_token,
            'refresh_token': self._refresh_token,
            'expiration_date': self._expiration_date,
            'lockout_date': self._lockout_date,
            'password_expired': self._password_expired,
        }

    def load_auth(self, auth_data: dict) -> None:
        """Load the authentication data from cache.

        Warning:
            `auth_data` is expected to carry the plaintext username and
            password (as produced by `dump_auth`). Only load this from a
            trusted, appropriately secured source.

        Args:
            auth_data (dict): Previously cached auth data, as returned by
                `dump_auth`.
        """
        self._username         = auth_data['username']
        self._password         = auth_data['password']
        self._api_key          = auth_data['api_key']
        self._secret_key       = auth_data['secret_key']
        self._access_token     = auth_data['access_token']
        self._refresh_token    = auth_data['refresh_token']
        self._expiration_date  = auth_data['expiration_date']
        self._lockout_date     = auth_data['lockout_date']
        self._password_expired = auth_data['password_expired']


    def _section_list_handler(self, rel_url: str, section_id: str | None = None, search_params: dict | None = None, parallel: bool = False) -> dict:
        """A generic section handler.

        This can be used to fetch a single entity specified by the section_id.
        this will be the unique UUID used by CRM.


        Args:
            rel_url (str): Relative API path for this resource, e.g. '/contacts'.
            section_id (str, optional): Id (UUID) of a single entity to
                fetch. When given, fetches that entity instead of listing.
                Defaults to None.
            search_params (dict, optional): Query string / search parameters
                for a list request. Defaults to None.
            parallel (bool, optional): Whether to fetch multiple pages in
                parallel when listing. Defaults to False.

        Returns:
            dict: Either the single entity (when section_id is given) or the
                (possibly paginated) listing.
        """
        logger.debug(
            f"Entered _section_list_handler: {rel_url} # {section_id} # {search_params} # {parallel}"
        )
        if section_id is not None:
            target_url = f"{rel_url}/{urllib.parse.quote_plus(str(section_id))}"

            req = self._make_request(
                'GET', target_url,
                headers=self._auth_headers(),
                get_params=search_params,
            )
            # If the ID exists the data is simply returned.
            section_result = req.json()
        else:
            target_url = rel_url
            if parallel:

                fetch_call = self._fetch_all_parallel
            else:
                fetch_call = self._fetch_all
            section_result = fetch_call(
                'GET', target_url,
                headers=self._auth_headers(),
                get_params=search_params,
            )

        return section_result

### Start API calls

    def activities(self, activity_id=None, search_params=None, parallel=False):
        '''Activities list, or fetch a single activity by id.
        '''
        return self._section_list_handler(
            '/activities',
            section_id=activity_id,
            search_params=search_params,
            parallel=parallel,
        )

    def activity_update(self, activity_id: str, activity_update: dict) -> bool:
        """Update an activity.

        Args:
            activity_id (str): Id of the activity to update.
            activity_update (dict): Fields to update on the activity.

        Returns:
            bool: True if the update succeeded (the response id matches
                activity_id), False otherwise.
        """
        req = self._make_request(
            'PUT',
            f'/activities/{activity_id}',
            json_data=activity_update,
            headers=self._auth_headers(),
        )

        req_data = req.json()

        return req_data['id'] == activity_id

    def contacts(self, contact_id=None, search_params=None, parallel=False):
        """List contacts meeting criteria, or fetch a single contact by id.

        Args:
            contact_id (str, optional): Fetch a single contact by id instead
                of listing. Defaults to None.
            search_params (dict, optional): Query string / search parameters.
                Defaults to None.
            parallel (bool, optional): Whether to fetch multiple pages in
                parallel. Defaults to False.

        Returns:
            dict: Either the single contact (if contact_id is given) or the
                (possibly paginated) listing.
        """
        return self._section_list_handler(
            '/contacts',
            section_id=contact_id,
            search_params=search_params,
            parallel=parallel,
        )

    def contact_services(self, contact_id: str) -> dict:
        '''Fetch a contact's services list.

        Docs:
        https://speca.io/CRM/backoffice-admin#list-contact-services
        '''
        req = self._make_request(
            'GET',
            f"/contacts/{contact_id}/services?"
            "include_order_info=true&include_subscription=true&include_total=true",
            headers=self._auth_headers(),
        )

        return req.json()

    def contact_subscriptions(self, contact_id: str) -> list:
        '''Fetch a contact's subscriptions list.'''
        req = self._make_request(
            'GET',
            f'/contacts/{contact_id}/subscriptions',
            headers=self._auth_headers(),
        )

        return req.json()['content']

    def contact_update(self, contact_id: str, contact_update: dict) -> bool:
        """Update a contact.

        Args:
            contact_id (str): Id of the contact to update.
            contact_update (dict): Fields to update on the contact.

        Returns:
            bool: True if the update succeeded (the response id matches
                contact_id), False otherwise.
        """
        req = self._make_request(
            'PUT',
            f'/contacts/{contact_id}',
            json_data=contact_update,
            headers=self._auth_headers(),
        )

        req_data = req.json()

        return req_data['id'] == contact_id

    def custom_fields(self, custom_field_id=None):
        """Get either all custom fields or a specific one.

        https://crmcom.stoplight.io/docs/stoplight-api-doc/9ae36ade79cf3-list-custom-fields

        Args:
            custom_field_id (str, optional): Fetch a single custom field by
                id instead of listing all. Defaults to None.

        Returns:
            dict: Either the single custom field (if custom_field_id is
                given) or the full listing.
        """
        if custom_field_id is not None:
            path = f'/custom_fields/{custom_field_id}'
        else:
            path = '/custom_fields'
        return self._section_list_handler(path)

    def devices(self, device_id=None, search_params=None, parallel=False):
        '''Get list of devices, or a single device by id.

        https://speca.io/CRM/backoffice-admin#list_devices
        '''
        return self._section_list_handler(
            '/devices',
            section_id=device_id,
            search_params=search_params,
            parallel=parallel,
        )

    def journals(self, journal_id=None, search_params=None, parallel=False):
        """Journals list, or fetch a single journal by id.

        Args:
            journal_id (str, optional): Journal ID to fetch. Defaults to None.
            search_params (dict, optional): Query string / search parameters.
                Defaults to None.
            parallel (bool, optional): Whether to fetch multiple pages in
                parallel. Defaults to False.

        Returns:
            dict: Either the single journal (if journal_id is given) or the
                (possibly paginated) listing.
        """
        return self._section_list_handler(
            '/journals',
            section_id=journal_id,
            search_params=search_params,
            parallel=parallel,
        )

    def orders(self, order_id=None, search_params=None, parallel=False):
        '''Orders list, or fetch a single order by id.
        '''
        return self._section_list_handler(
            '/orders',
            section_id=order_id,
            search_params=search_params,
            parallel=parallel,
        )

    def products(self, product_id=None, search_params=None, parallel=False):
        '''Fetch product list, or a single product by id.
        '''
        return self._section_list_handler(
            '/products',
            section_id=product_id,
            search_params=search_params,
            parallel=parallel,
        )

    def product_components(self, product_id, search_params=None):
        '''Get list of product components.
        '''
        req = self._make_request(
            'GET',
            f"/products/{product_id}/components",
            headers=self._auth_headers(),
        )

        return req.json()

    def product_prices(self, product_id):
        '''Get list of product prices.
        '''
        req = self._make_request(
            'GET',
            f"/products/{product_id}/prices",
            headers=self._auth_headers(),
        )

        return req.json()

    def product_provisioning_providers(self, product_id):
        '''Product Provisioning Providers.

        API:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/841b6f1efed20-list-product-provisioning-providers
        '''
        req = self._make_request(
            'GET',
            f"/products/{product_id}/providers",
            headers=self._auth_headers(),
        )

        return req.json()

    def sales_models(self, search_params=None, parallel=False):
        """Sales models.

        API Documentation:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/88466722bdd5c-list-sales-models
        """
        return self._section_list_handler(
            '/sales_models',
            search_params=search_params,
            parallel=parallel,
        )

    def service_devices(self, service_id: str) -> dict:
        '''Fetch a service's device list.

        Docs:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/0745b67da81df-list-service-devices
        '''
        return self._section_list_handler(f'/services/{service_id}/devices')

    def service_recommendation(self, **kwargs):
        """Generate service recommendations.

        URL:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/db24325a4a173-service-
        """
        search_params = {}
        accepted_params = [
            'product_id',
            'service_id',
        ]
        for current_param in accepted_params:
            if current_param in kwargs:
                search_params[current_param] = kwargs[current_param]

        return self._section_list_handler(
            '/services/recommendation',
            search_params=search_params,
        )

    def service_requests(self, service_request_id=None, search_params=None, parallel=False):
        '''Service Requests list, or fetch a single service request by id.
        '''
        return self._section_list_handler(
            '/service_requests',
            section_id=service_request_id,
            search_params=search_params,
            parallel=parallel,
        )

    def service_update(self, service_id: str, update_body: dict):
        """Update service API call.

        API Documentation:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/339e1a0af4eab-update-service

        Args:
            service_id (str): Service ID
            update_body (dict): Body of request
        """
        req = self._make_request(
            'PUT',
            f'/services/{service_id}',
            headers=self._auth_headers(),
            json_data=update_body,
        )

        return req.json()

    def subscriptions(self, subscription_id=None, search_params=None, parallel=False):
        """Fetch subscriptions list, or a single subscription by id.

        Args:
            subscription_id (str, optional): Fetch a single subscription by
                id instead of listing. Defaults to None.
            search_params (dict, optional): Query string / search parameters.
                Defaults to None.
            parallel (bool, optional): Whether to fetch multiple pages in
                parallel. Defaults to False.

        Returns:
            dict: Either the single subscription (if subscription_id is
                given) or the (possibly paginated) listing.
        """
        return self._section_list_handler(
            '/subscriptions',
            section_id=subscription_id,
            search_params=search_params,
            parallel=parallel,
        )

    def subscription_devices(self, subscription_id: str) -> list:
        '''Fetch a subscription's device list.'''
        req = self._make_request(
            'GET',
            f'/subscriptions/{subscription_id}/devices',
            headers=self._auth_headers(),
        )

        return req.json()['content']

    def subscription_update(self, subscription_id: str, update_body: dict):
        """Update subscription API call.

        API Documentation:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/f4ad7c1a7ba99-update-subscription

        Args:
            subscription_id (str): Subscription ID
            update_body (dict): Body of request
        """
        req = self._make_request(
            'PUT',
            f'/subscriptions/{subscription_id}',
            headers=self._auth_headers(),
            json_data=update_body,
        )

        return req.json()

    def teams(self, user_id=None, search_params=None, parallel=False):
        '''Teams list, or fetch a single team by id.
        '''
        return self._section_list_handler(
            '/teams',
            section_id=user_id,
            search_params=search_params,
            parallel=parallel,
        )

    def users(self, user_id=None, search_params=None, parallel=False):
        '''Users list, or fetch a single user by id.
        '''
        return self._section_list_handler(
            '/users',
            section_id=user_id,
            search_params=search_params,
            parallel=parallel,
        )

### Deprecated aliases
#
# These wrap the methods above under their old names so existing callers
# keep working. Each call logs a warning (and raises a DeprecationWarning)
# naming the replacement to migrate to; once your logs stop showing calls
# to a given name, it's safe to delete that alias.

    @_deprecated('activities')
    def activities_list(self, activity_id=None, search_params=None, parallel=False):
        return self.activities(activity_id, search_params, parallel)

    @_deprecated('contacts')
    def contacts_list(self, contact_id=None, search_params=None, parallel=False):
        return self.contacts(contact_id, search_params, parallel)

    @_deprecated('contact_services')
    def contact_services_list(self, contact_id=None):
        return self.contact_services(contact_id)

    @_deprecated('contact_services')
    def list_contact_services(self, contact_id: str):
        return self.contact_services(contact_id)

    @_deprecated('contact_subscriptions')
    def contact_subscription_list(self, contact_id=None):
        return self.contact_subscriptions(contact_id)

    @_deprecated('devices')
    def devices_list(self, device_id=None, search_params=None, parallel=False):
        return self.devices(device_id, search_params, parallel)

    @_deprecated('journals')
    def journals_list(self, journal_id=None, search_params=None, parallel=False):
        return self.journals(journal_id, search_params, parallel)

    @_deprecated('orders')
    def orders_list(self, order_id=None, search_params=None):
        return self.orders(order_id, search_params)

    @_deprecated('products')
    def products_list(self, product_id=None, search_params=None):
        return self.products(product_id, search_params)

    @_deprecated('sales_models')
    def sales_model(self):
        return self.sales_models()

    @_deprecated('service_devices')
    def service_device_list(self, service_id: str):
        return self.service_devices(service_id)

    @_deprecated('service_devices')
    def list_service_devices(self, service_id: str) -> dict:
        return self.service_devices(service_id)

    @_deprecated('service_requests')
    def service_requests_list(self, service_requests_id=None, search_params=None, parallel=False):
        return self.service_requests(service_requests_id, search_params, parallel)

    @_deprecated('subscriptions')
    def subscriptions_list(self, subscriptions_id=None, search_params=None, parallel=False):
        return self.subscriptions(subscriptions_id, search_params, parallel)

    @_deprecated('subscriptions')
    def subscription(self, subscription_id: str | None = None):
        return self.subscriptions(subscription_id)

    @_deprecated('subscription_devices')
    def subscriptions_devices_list(self, subscription_id):
        return self.subscription_devices(subscription_id)

    @_deprecated('teams')
    def teams_list(self, user_id=None, search_params=None):
        return self.teams(user_id, search_params)

    @_deprecated('users')
    def users_list(self, user_id=None, search_params=None):
        return self.users(user_id, search_params)

if __name__ == '__main__':
    import datetime
    import os
    import pprint
    import sys
    import tracemalloc

    # External imports
    import dotenv


    dotenv.load_dotenv()
    logging.getLogger('connectionpool').setLevel(logging.DEBUG)
    logging.basicConfig(
        format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
    )

    api = CRM5BackofficeAdmin('app.crm.com')
    # api.debug(False)
    api.login(
        # Pull from .env
        username   = os.environ.get('CRM_USERNAME'),
        password   = os.environ.get('CRM_PASSWORD'),
        api_key    = os.environ.get('API_KEY'),
        secret_key = os.environ.get('SECRET_KEY'),
    )

    start = datetime.datetime.now()
    # tracemalloc.start()

    contact_account = '63ca00d7-57a4-4ca5-ab76-cda37e8cbd64'
    contact_res = api.contacts(search_params={
        'email_address': 'ameena.mm34@gmail.com',
        #'custom_fields': f"account_number;{contact_account}",
        # 'include_custom_fields': 'true',
    })
    pprint.pprint(contact_res)
    # contact = contact_res['content'][0]
    # services_res = api.devices_list(search_params={'contact_id': contact['id']})
    # pprint.pprint(services_res)
    # devices_res = api.devices_list(search_params={'serial_number': '0100000000002'})
    # pprint.pprint(devices_res)

    #api.contacts_device_list()

    # for curr_id in ids.split():
    #     print("Processing: {curr_id}")
    #     curr_contact = api.contacts_list(search_params={
    #         'custom_fields': f"account_number;{curr_id}",
    #         'include_custom_fields': 'true',
    #     })
    #     pprint.pprint(curr_contact['content'])
    #     curr_subscription = api.subscriptions_list(
    #         search_params={'contact_id': curr_contact['content'][0]['id']}
    #     )
    #     pprint.pprint(curr_subscription)
    #     api.subscription_update(curr_subscription['content'][0]['id'], {
    #         'action': 'CANCEL',
    #     })
    end = datetime.datetime.now()
    duration_sec = (end - start).total_seconds()
    # pprint.pprint(curr_contact['content'], width=120)
    # pprint.pprint(result)

    # traced_memory = tracemalloc.get_traced_memory()
    # print(f"Memory stats: {traced_memory}")
    # tracemalloc.stop()
    print(f"Duration: {duration_sec}")
