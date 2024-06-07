'''CRM 5 Backoffice APIs.

This is the REST API documented at:
https://speca.io/CRM/backoffice-admin#introduction

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

class CRM5BackofficeAdmin:
    '''CRM.com BackOffice Admin API.

    API Docs:
    https://speca.io/CRM/backoffice-admin
    '''
    _backoffice_url = '/backoffice/v1'


    def __init__(self, crm_domain) -> None:
        '''Constructor'''
        self._crm_domain = crm_domain
        self._username = None
        self._password = None
        self._api_key = None
        self._secret_key = None
        self._access_token = None
        self._refresh_token = None
        self._debug_state = False
        self._timeout = 60
        self._default_page_size = 100

    def debug(self, debug_state: bool=None) -> bool:
        '''Get / Set debug state.

        if a debug_state is passed then set the debug state and logging
        parameters. If None is set then simply return the value.
        '''
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
        '''Build the full URL for making a request.

        Builds the full url.
        '''
        base_url = f"{self._backoffice_url}{relative_url}"

        return urllib.parse.urljoin(f"https://{self._crm_domain}", base_url)

    def _make_request(self, method, url, json_data=None, headers=None, get_params=None):
        '''Make a request to the CRM api.
        '''

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
            raise RuntimeError(f"HTTP Error '{req.status_code}' -> {req.text}")

        return req

    def _fetch_all(self, method, url, json_data=None, headers=None, get_params=None):
        '''Make iterative requests to fetch the complete result set.
        '''

        if get_params is None:
            get_params = {}
        if 'size' not in get_params:
            get_params['size'] = self._default_page_size

        req = self._make_request(method, url, json_data, headers, get_params)

        req_data = req.json()
        page_size = int(req_data['paging']['size'])
        total_records = int(req_data['paging']['total'])
        logger.debug(f"First page data: {req_data['paging']}")
        if page_size >= total_records:
            return req_data

        pages = math.ceil(total_records / page_size)
        if get_params is None:
            get_params = {}

        if 'size' not in get_params or get_params['size'] != page_size:
            get_params['size'] = page_size

        for curr_page in range(2, pages + 1):
            logger.debug(f"Fetching page: {curr_page}")
            get_params['page'] = curr_page
            curr_page_req = self._make_request(
                method,
                url,
                json_data,
                headers,
                get_params
            )
            curr_page_req_data = curr_page_req.json()
            req_data['content'].extend(curr_page_req_data['content'])

        req_data['paging']['page'] = -1

        return req_data

    def login(self, username: str, password: str, api_key: str, secret_key: str) -> bool:
        '''Authenticate user.

        Docs:
        https://speca.io/CRM/backoffice-admin#adminusers-authenticate

        '''
        self._username = username
        self._password = password
        self._api_key = api_key
        self._secret_key = secret_key

        req = self._make_request('POST', '/users/authenticate',
            json_data={
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

        return

    def logout(self,) -> None:
        '''Logout from API and invalidate tokens.
        '''
        return

    def _section_list_handler(self, rel_url, section_id=None, search_params=None):
        '''
        '''

        if section_id is not None:
            product_url = f"{rel_url}/{section_id}"

            section_result = self._make_request(
                'GET', product_url,
                headers={
                    'authorization': self._access_token,
                    'api_key':       self._secret_key,
                },
                get_params=search_params,
            )
        else:
            section_result = self._fetch_all(
                'GET', rel_url,
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

    def contacts_list(self, contact_id=None, search_params=None):
        '''Get list of devices.
        '''
        return self._section_list_handler(
            '/contacts',
            section_id=contact_id,
            search_params=search_params,
        )

    def devices_list(self, devices_id=None, search_params=None):
        '''Get list of devices.

        https://speca.io/CRM/backoffice-admin#list_devices
        '''
        return self._section_list_handler(
            '/devices',
            section_id=devices_id,
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
        '''Activities list.

        '''
        return self._section_list_handler(
            '/products',
            section_id=product_id,
            search_params=search_params,
        )

    def services_list(self, service_id=None, search_params=None):
        '''Services list.

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

    def subscriptions_list(self, subscriptions_id=None, search_params=None):
        '''Subscriptions list.

        '''
        return self._section_list_handler(
            '/subscriptions',
            section_id=subscriptions_id,
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
        '''Get list of products.

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
            f'/contacts/{contact_id}/services',
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
        req = self._make_request('GET', f"/contacts/{contact_id}/services",
            headers={
                'authorization': self._access_token,
                'api_key': self._secret_key,
            },
        )
        product_data = req.json()

        return product_data

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
    import os
    import pprint

    # External imports
    import dotenv


    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)

    api = CRM5BackofficeAdmin('app.crm.com')
    # api.debug(True)
    api.login(
        # Pull from .env
        username   = os.environ.get('CRM_USERNAME'),
        password   = os.environ.get('CRM_PASSWORD'),
        api_key    = os.environ.get('API_KEY'),
        secret_key = os.environ.get('SECRET_KEY'),
    )
    # product_result = api.products(search_params={'search_value': 'VILO'})
    start = datetime.datetime.now()
    contact_list = api.contacts_list(search_params={'code': 7038476})
    pprint.pprint(contact_list)
    pprint.pprint(contact_list['content'][0]['id'])

    # contact_subscriptions = api.subscriptions_list(
    #     search_params={
    #         'contact_id': contact_list['content'][0]['id'],
    #         'include_billing_info': 'true',
    #     },
    # )
    # pprint.pprint(contact_subscriptions)
    # subscription_devices = api.devices_list(search_params={
    #     'contact_id': contact_list['content'][0]['id'],
    #     'subscription_ids': contact_subscriptions['content'][0]['id'],
    #     'include_subscription': 'true',
    # })
    # pprint.pprint(subscription_devices, width=200)
    # device_service = api.services_list(
    #     # service_id=subscription_devices['content'][0]['enabled_services'][0]['id']
    # )
    # pprint.pprint(device_service)
    services_list = api.contact_services_list(contact_list['content'][0]['id'])
    pprint.pprint(services_list)
    end = datetime.datetime.now()
    duration_sec = (end - start).total_seconds()

    print(f"Duration: {duration_sec}")
