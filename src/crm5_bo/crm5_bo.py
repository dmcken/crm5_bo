'''CRM 5 Backoffice APIs.

'''

# System imports
import http.client
import logging
import math
import urllib.parse

# External imports
import requests


http_logger = logging.getLogger('httplogger')
logger = logging.getLogger(__name__)

class CRM5APIError(RuntimeError):
    """CRM 5 API Errors.

    Args:
        RuntimeError (_type_): _description_

    Raises:
        RuntimeError: _description_

    Returns:
        _type_: _description_
    """

class CRM5BackofficeAdmin:
    '''CRM.com BackOffice Admin API.

    API Docs (current version v2):
    https://crmcom.stoplight.io/docs/stoplight-api-doc/
    '''
    _backoffice_url = '/backoffice/v2'


    def __init__(self, crm_domain: str) -> None:
        """Constructor.

        Args:
            crm_domain (str): _description_
        """
        self._crm_domain        = crm_domain
        self._username          = None
        self._password          = None
        self._api_key           = None
        self._secret_key        = None
        self._access_token      = None
        self._refresh_token     = None
        self._debug_state       = False
        self._timeout           = 60
        self._default_page_size = 100
        self._expiration_date   = None
        self._organization_mod  = None
        self._lockout_date      = None
        self._password_expired  = None

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

    def debug(self, debug_state: bool=None) -> bool:
        """Get / Set debug state.

        if a debug_state is passed then set the debug state and logging
        parameters. If None is set then simply return the value.

        Args:
            debug_state (bool, optional): _description_. Defaults to None.

        Returns:
            bool: _description_
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
            relative_url (str): _description_

        Returns:
            str: _description_
        """
        base_url = f"{self._backoffice_url}{relative_url}"

        return urllib.parse.urljoin(f"https://{self._crm_domain}", base_url)

    def _make_request(self, method, url, json_data=None, headers=None,
                      get_params=None) -> dict:
        """Make a request to the CRM api.

        Args:
            method (_type_): HTTP method to use.
            url (_type_): URL to request.
            json_data (_type_, optional): JSON data to post. Defaults to None.
            headers (_type_, optional): Headers to use for request. Defaults to None.
            get_params (_type_, optional): If this is a HTTP GET the URL query parameters. Defaults to None.

        Raises:
            RuntimeError: _description_

        Returns:
            dict: _description_
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

        if req.status_code != 200:
            # Error we need to handle
            if self._debug_state:
                logger.error(f"Recv error code: {req.status_code}")
                logger.error(f"Body: {req.text}")
            raise CRM5APIError(f"HTTP Error '{req.status_code}' -> {req.text}")

        return req

    def _fetch_page(self, method: str, url: str, json_data=None, headers=None,
                    get_params=None, page_num: int=None):
        """Fetch a single page of a query.

        Args:
            method (str): _description_
            url (str): _description_
            json_data (_type_, optional): _description_. Defaults to None.
            headers (_type_, optional): _description_. Defaults to None.
            get_params (_type_, optional): _description_. Defaults to None.
            page_num (int, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        if get_params is None:
            get_params = {}
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

    def _fetch_all(self, method: str, url: str, json_data=None, headers=None, get_params=None) -> dict:
        """Make iterative requests to fetch the complete result set.

        Args:
            method (str): _description_
            url (str): _description_
            json_data (_type_, optional): _description_. Defaults to None.
            headers (_type_, optional): _description_. Defaults to None.
            get_params (_type_, optional): _description_. Defaults to None.

        Returns:
            dict: _description_
        """
        logger.debug(f"Fetch all {method} -> {url}")
        if get_params is None:
            get_params = {}
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
        total_records = int(req_data['paging']['total'])

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

        return

    def logout(self) -> None:
        """Logout of API.

        Logout from API and invalidate access and refresh tokens.

        """
        return

    def dump_auth(self,) -> dict:
        """Dump the authentication data for cache.

        Returns:
            dict: _description_
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

        Args:
            auth_data (dict): _description_
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


    def _section_list_handler(self, rel_url, section_id=None, search_params=None):
        """A generic section handler.

        This can be used to fetch a single entity specified by the section_id.
        this will be the unique UUID used by CRM.


        Args:
            rel_url (_type_): _description_
            section_id (_type_, optional): _description_. Defaults to None.
            search_params (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        if section_id is not None:
            target_url = f"{rel_url}/{section_id}"

            req = self._make_request(
                'GET', target_url,
                headers={
                    'authorization': self._access_token,
                    'api_key':       self._secret_key,
                },
                get_params=search_params,
            )
            # If the ID exists the data is simply returned.
            section_result = req.json()
        else:
            target_url = rel_url
            section_result = self._fetch_all(
                'GET', target_url,
                headers={
                    'authorization': self._access_token,
                    'api_key':       self._secret_key,
                },
                get_params=search_params,
            )

        return section_result

    def activities_list(self, activity_id=None, search_params=None):
        '''Activities list.

        '''
        return self._section_list_handler(
            '/activities',
            section_id=activity_id,
            search_params=search_params,
        )

    def activity_update(self, activity_id: str, activity_update: dict) -> bool:
        """Update an activity.

        Args:
            activity_id (str): _description_
            activity_update (dict): _description_

        Returns:
            bool: _description_
        """

        req = self._make_request(
            'PUT',
            f'/activities/{activity_id}',
            json_data=activity_update,
            headers={
                'authorization': self._access_token,
                'api_key':       self._secret_key,
            },
        )

        req_data = req.json()

        if req_data['id'] == activity_id:
            return True

        return False

    def contacts_list(self, contact_id=None, search_params=None):
        '''Get list of devices.
        '''
        return self._section_list_handler(
            '/contacts',
            section_id=contact_id,
            search_params=search_params,
        )

    def custom_fields(self, custom_field_id=None):
        """Get either all custom fields or a specific one.

        https://crmcom.stoplight.io/docs/stoplight-api-doc/9ae36ade79cf3-list-custom-fields

        Args:
            id (_type_, optional): _description_. Defaults to None.
        """
        if custom_field_id is not None:
            path = f'/custom_fields/{custom_field_id}'
        else:
            path = '/custom_fields'
        return self._section_list_handler(path)


    def devices_list(self, search_params=None):
        '''Get list of devices.

        https://speca.io/CRM/backoffice-admin#list_devices
        '''
        return self._section_list_handler(
            '/devices',
            search_params=search_params,
        )

    def journals_list(self, service_id=None, search_params=None):
        '''Services list.

        '''
        return self._section_list_handler(
            '/journals',
            section_id=service_id,
            search_params=search_params,
        )

    def orders_list(self, order_id=None, search_params=None):
        '''Orders list.

        '''
        return self._section_list_handler(
            '/orders',
            section_id=order_id,
            search_params=search_params,
        )

    def products_list(self, product_id=None, search_params=None):
        '''Fetch Product list.

        '''
        return self._section_list_handler(
            '/products',
            section_id=product_id,
            search_params=search_params,
        )

    @DeprecationWarning
    def services_list(self, service_id=None, search_params=None):
        '''Services list.

        REST endpoint no longer exists in v2 API.

        '''
        return self._section_list_handler(
            '/services',
            section_id=service_id,
            search_params=search_params,
        )

    def service_requests_list(self, service_requests_id=None, search_params=None):
        '''Service Requests list.

        '''
        return self._section_list_handler(
            '/service_requests',
            section_id=service_requests_id,
            search_params=search_params,
        )

    def service_device_list(self, service_id: str):
        '''Fetch service device list.
        '''
        return self._section_list_handler(
            f'/services/{service_id}/devices',
        )

    def subscriptions_list(self, subscriptions_id=None, search_params=None):
        """Fetch subscriptions list.

        Args:
            subscriptions_id (_type_, optional): _description_. Defaults to None.
            search_params (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        return self._section_list_handler(
            '/subscriptions',
            section_id=subscriptions_id,
            search_params=search_params,
        )

    def teams_list(self, user_id=None, search_params=None):
        '''Users list.

        '''
        return self._section_list_handler(
            '/teams',
            section_id=user_id,
            search_params=search_params,
        )

    def users_list(self, user_id=None, search_params=None):
        '''Users list.

        '''
        return self._section_list_handler(
            '/users',
            section_id=user_id,
            search_params=search_params,
        )

    def products(self, product_id=None, search_params=None):
        '''Get list of products.

        product_data = api.products()

        with open('products.txt','w') as f:
            f.write(pprint.pformat(product_data))
        '''

        if product_id is not None:
            product_url = f"/products/{product_id}"
        else:
            product_url = "/products"

        if search_params is None:
            search_params={}

        search_params['size'] = self

        req = self._make_request('GET', product_url,
            headers={
                'authorization': self._access_token,
                'api_key':       self._secret_key,
            },
            get_params=search_params,
        )
        product_data = req.json()

        # product_data contains content and paging
        # paging looks like the following:
        # 'paging': {'page': 1, 'size': 75, 'total': 75}

        return product_data

    def contacts(self, contact_id=None, search_params=None):
        '''Get list of contacts.

        product_data = api.products()

        with open('products.txt','w') as f:
            f.write(pprint.pformat(product_data))
        '''

        if contact_id is not None:
            contact_url = f"/contacts/{contact_id}"
        else:
            contact_url = "/contacts"

        if search_params is None:
            search_params={}

        search_params['size'] = self._default_page_size

        req = self._make_request('GET', contact_url,
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
            get_params=search_params,
        )
        product_data = req.json()

        # product_data contains content and paging
        # paging looks like the following:
        # 'paging': {'page': 1, 'size': 75, 'total': 75}

        return product_data

    def contact_subscription_list(self, contact_id=None):
        '''Contact Subscriptions list.

        Getting unauthorized.
        '''
        result = self._make_request("GET", f'/contacts/{contact_id}/subscriptions')

        data = result.json()

        return data['content']

    def contact_services_list(self, contact_id=None):
        '''Contact Services List.

        Getting unauthorized.
        '''
        result = self._make_request(
            "GET",
            f'/contacts/{contact_id}/services?include_subscription=true',
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
        )

        data = result.json()

        return data

    def subscriptions_devices_list(self, subscription_id):
        '''Fetch subscription devices list.
        '''
        result = self._make_request("GET", f'/subscriptions/{subscription_id}/devices')

        data = result.json()

        return data['content']

    def list_contact_services(self, contact_id: str):
        '''List contact services.

        Docs:
        https://speca.io/CRM/backoffice-admin#list-contact-services


        '''
        # ?size=100&include_subscription=true
        req = self._make_request('GET', f"/contacts/{contact_id}/services?" + \
            "include_order_info=true&include_subscription=true&include_total=true",
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
        )
        product_data = req.json()

        return product_data

    def list_service_devices(self, service_id: str) -> dict:
        """List Service Devices

        Docs:
        https://crmcom.stoplight.io/docs/stoplight-api-doc/0745b67da81df-list-service-devices

        Args:
            service_id (str): _description_

        Returns:
            dict: _description_
        """
        req = self._make_request('GET', f"/services/{service_id}/devices",
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
        )
        device_data = req.json()

        return device_data

    def subscription(self, subscription_id: str = None):
        '''Subscriptions.
        '''
        if subscription_id is None:
            final_url = '/subscriptions'
        else:
            subscription_id_encoded = urllib.parse.quote_plus(subscription_id)
            final_url = f"/subscriptions/{subscription_id_encoded}"

        req = self._make_request('GET', final_url,
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
        )
        subscription_data = req.json()

        return subscription_data


if __name__ == '__main__':
    import datetime
    import json
    import os
    import pprint

    # External imports
    import dotenv


    dotenv.load_dotenv()
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
    )

    api = CRM5BackofficeAdmin('app.crm.com')
    api.debug(True)
    try:
        with open('auth.json', 'r', encoding='utf-8') as f:
            auth_data = json.loads(f.read())
        one_hr_future = (datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()
        logging.info(f"Exp: {auth_data['expiration_date']} -> {one_hr_future}")
        if int(auth_data['expiration_date']) <= one_hr_future:
            # If the expiration date is down to an hour.
            raise FileNotFoundError
        api.load_auth(auth_data=auth_data)
    except FileNotFoundError:
        logging.info("Creating new token")
        api.login(
            # Pull from .env
            username   = os.environ.get('CRM_USERNAME'),
            password   = os.environ.get('CRM_PASSWORD'),
            api_key    = os.environ.get('API_KEY'),
            secret_key = os.environ.get('SECRET_KEY'),
        )
        # Save the token
        with open('auth.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(api.dump_auth()))
    start = datetime.datetime.now()

    devices = api.activities_list(
        search_params={
            'custom_fields': 'activity_number;A005090',
            'include_custom_fields': True,
        }
    )

    print("Result")
    pprint.pprint(devices)

    api.activity_update(
        devices['content'][0]['id'],
        {
            # This overwrites all custom fields.
            'custom_fields': [
                {'key': 'status','value': 'Scheduled'}

            ]
        }
    )
    end = datetime.datetime.now()
    duration_sec = (end - start).total_seconds()

    print(f"Duration: {duration_sec}")
