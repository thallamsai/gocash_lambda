""" Module to Load Money into GoCash Account """
from golambda.Action import GoibiboAction
from golambda.middleware.gocash import GocashMiddleware
from golambda.Lambda import Lambda
import requests
import logging
logger = logging.getLogger(__name__)

class GoCashLoadUPI(GoibiboAction):
    """ Class will allow loading NPGC into Gocash Wallet """
    INIT_URL = 'http://www.goibibo.com/gocash/initiate_gocash_credit/'
    CREDIT_URL = 'http://gocash.goibibo.com/v2/gocash/complete_credit/'

    def __init__(self, **kwargs):
        self.intent_name = 'load_wallet'
        self.MESSAGE_NAMESPACE = 'gocash_messages'
        super(GoCashLoadUPI, self).__init__(**kwargs)
        self.intent_obj = kwargs.get('intent_obj')
        self.email = self.intent_obj.email
        self.amount = self.intent_obj.amount
        if(self.amount):
            self.amount = self.amount[0]
        gocash_response = GocashMiddleware.user_balance(self.email)
        if gocash_response.json().get('success'):
            self.wallet_user = True
            self.gocash_data = gocash_response.json()['data']
        else:
            self.wallet_user = False

    def _initiate_credit(self):
        post_data = {
            'email': self.email,
            'npgc': str(self.amount),
            'type': 'load_wallet',
            'vertical': 'whatsapp'
        }
        data = requests.post(self.__class__.INIT_URL, data=post_data).json()
        paymentid = data['data']['transaction']['gocash_txn_id']
        return paymentid

    def action(self):
        resp = self.base_resp
        message = None

        if(self.amount):
            data = self.get_payment_intent(self.amount, self._initiate_credit())
            resp = {
                'action': 'redirect',
                'data': {
                    'to_intent': 'pay.collect.payment',
                    'skipNLP': True
                },
                'success': True
            }
            resp['data'].update(data)
        elif self.wallet_user:
            message = self.MESSAGES['ask_upi_load_amount']
            resp['action'] = 'new_prompt'
            resp['entities'] = self.get_init_entities()
        else:
            message = self.MESSAGES['gocash_account_not_found']
        if(message):
            resp['message'] = message
        return resp

    def get_init_entities(self):
        entities = {
            "subIntent": "initiate",
        }
        return entities

    def get_payment_intent(self, amount, paymentid):
        vertical_data = {
             'firstname': '',
             'lastname': '',
             'is_domestic': True,
             'product_type': 'load_wallet',
             'vertical_message': 'To load money in your GoCash wallet pay using UPI',
             'payment_link': '',
             'unique_count': 1,
             'bookingid': '',
             'email': self.email,
             'actual_flavour': unicode("whatsapp")
        }
        entities = {
            "paymentid": paymentid,
            "payment_mode": unicode("UPI"),
            "channel": unicode("whatsapp"),
            "vertical": unicode("gocash"),
            "amount": unicode(amount),
            "vertical_data": vertical_data,
            "mobile": self.mobile
        }
        next_intents = Lambda.fetch_actions(
            self.vertical,
            entity=entities,
            intent_obj=self.intent_obj,
            intent_list=[
                {
                     'intent': 'pay.collect.payment',
                     'subIntent': 'default',
                     'message': 'Yes'
                }
             ]
        )
        return entities


class GoCashLoadUPIComplete(GoCashLoadUPI):
    def __init__(self, **kwargs):
        self.subintent_name = 'complete'
        super(GoCashLoadUPIComplete, self).__init__(**kwargs)
        self.paymentid = self.intent_obj.paymentid
        self.callback_data = self.intent_obj.callback_data

    def action(self):
        resp = self.base_resp
        data = {
            'gocash_txn_id': self.paymentid
        }
        amount = self.callback_data['amount']
        if self.callback_data.get('status', 'failure') == 'success':
            response = requests.post(self.__class__.CREDIT_URL, json=data)
            if response.status_code == 200:
                balance = response.json()['data']['transactions'][0]['data']['balance']['end']
                resp['message'] = self.MESSAGES['gocash_account_filled'].format(
                    amount=amount,
                    gocash=balance['p_bal'],
                    gocashplus=balance['np_bal']+balance['b_bal']
                )
            else:
                resp['message'] = self.MESSAGES['error_filling_wallet']
        else:
            resp['message'] = self.MESSAGES['failure_in_payment']
        return resp


class GoCashLoadUPIInitiate(GoCashLoadUPI):
    def __init__(self, **kwargs):
        self.subintent_name = 'initiate'
        super(GoCashLoadUPIInitiate, self).__init__(**kwargs)

    def action(self):
        data = self.get_payment_intent(self.amount, self._initiate_credit())

        resp = {
                'action': 'redirect',
                'data': {
                   'to_intent': 'pay.collect.payment',
                   'skipNLP': True
                },
                'success': True
        }
        resp['data'].update(data)
        '''
        resp = self.call_another_action(
            parent_intent=self.intent_name,
            new_intent='pay.collect.payment',
            subIntent="default",
            data=data
        )
        '''
        return resp

