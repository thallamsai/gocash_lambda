import logging
from datetime import datetime
from cache_managment.redis_layer import CachingScope

from golambda.Action import GoibiboAction
from gocash_lambda.golambda_vertical.goibibo.gocash.intents import GoCashCashbackNotReceived, GiftNotReceived, GocashBalance, GocashTandC, \
    GocashRedemption, ReactUpgrade
from golambda.middleware.booking import BookingMiddleware
from golambda.Lambda import Lambda
from gocash_lambda.golambda_vertical.goibibo.gocash.load import GoCashLoadUPI, GoCashLoadUPIInitiate, GoCashLoadUPIComplete
from golambda.response.Response import Message, Response

from gocash_lambda.golambda_vertical.goibibo.gocash import intents

from golambda.middleware.booking import BookingMiddleware

from golambda.middleware.gocash import GocashMiddleware
import requests
import traceback
import json

logger = logging.getLogger(__name__)


class GoCashCashbackNotReceivedAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = "gocash.cashback_not_received"
        super(GoCashCashbackNotReceivedAction, self).__init__(**kwargs)

    def action(self):
        obj = self.intent_obj

        response = {
            'template': 'text',
            'data': {},
            'next_intents': Lambda.fetch_actions("", entity={'user_email': obj.email},
                                                 intent_list=[{'intent': "gocash.how_to_redeem"},
                                                              {'intent': "gocash.gocash_summary"},
                                                              {'intent': "gocash.gocash_t&c"}], intent_obj = obj),
            'success': True,
            'action': 'endWithResult'
        }
        booking_id = obj.booking_id if hasattr(obj, "booking_id") else None
        vertical =''
        if booking_id:
            try:

                if 'HTL' in booking_id.upper():
                    vertical = 'hotels'
                elif 'FL' in booking_id.upper():
                    vertical = 'flights'
                else:
                    response['message'] = "goCash+ information for the provided booking ID could not be found. " \
                                          "Please contact the CRM team."
                    response['success'] = True

                if response['success']:
                    middleware_response = BookingMiddleware.getBookingData(booking_id)
                    if middleware_response[vertical][0]['db_status'] != 'to deliver':
                        response['message'] = "goCash+ information for the provided booking ID could not be found. " \
                                              "Please contact the CRM team."
                        response['success'] = True
                    else:
                        cashback_val = middleware_response[vertical][0][vertical[:-1]].get('gocash_cash_back_value', 0)
                        credit_date_string = middleware_response[vertical][0][vertical[:-1]]['bon']['date']
                        credit_date = datetime.strptime(credit_date_string, "%Y-%m-%d %H:%M:%S")
                        if cashback_val > 0:

                            if middleware_response[vertical][0][vertical[:-1]].get('gocash_processed'):
                                response['message'] = "goCash+ amount of %d has already been processed for the given booking" \
                                                      % cashback_val

                                response['success'] = True
                            else:
                                if credit_date > datetime.now():
                                    response['message'] = "goCash+ amount of %d will be credited to you for the given " \
                                                          "booking after the completion of your trip." % cashback_val

                                    response['success'] = True
                                else:

                                    try:

                                        url = "http://gocash.goibibo.com/v2/gocash/credit/"
                                        payload = {"user_email":obj.email,
                                                   "type": "promo",
                                                   "promotional_amount": cashback_val,
                                                   "vertical" : "Gocash",
                                                   "bucket_amount" : 0,
                                                   "non_promotional_amount" : 0,
                                                   "application" : "cashback",
                                                   "txn_id" : obj.booking_id,
                                                   "extra_params" : {"client_remarks" : "cashback"}
                                                   }
                                        headers = {
                                            'Content-Type': "application/json"
                                        }
                                        cr_response = requests.request("POST", url, data=payload, headers=headers)
                                        response['message'] = "The booking ID provided is eligible for a goCash+ cashback " \
                                                            "amount of {} which has been credited now. ".format(cashback_val)

                                    except Exception:

                                        response['message'] = "The booking ID provided is eligible for a goCash+ cashback " \
                                                          "amount of {}. Please contact CRM team to help in credit.".format(cashback_val)

                                    response['success'] = True
                        else:
                            response['message'] = "The booking ID provided by you is not eligible for cashback."

                            response['success'] = True
            except Exception as e:

                logger.error('gocash - cashback not received' + traceback.format_exc())

                response['message'] = "goCash+ information corresponding to the booking ID provided by you is not found."

                response['success'] = True

        else:
            try:
                email = obj.email if hasattr(obj, "email") else None
                if not email:
                    raise Exception
                vertical = obj.vertical if hasattr(obj, "vertical") else "flights|hotels"
                #bookings = BookingMiddleware.get_user_booking_history(email=email, Pagination=5, verticals=vertical)
                bookings_list = []
                #query = self.__get_query_showbookings__(
                    # paymentid=paymentid, lid=lid, pastbookings=self.pastbookings)
                hints = {"$orderby": {"departure": -1},
                         "$fields": self.__class__.REQUIRED_CARD_FIELDS}
                cursor = self.ejdb.find('booking', hints=hints)
                #flights = bookings.get("flights", [])
                #hotels = bookings.get("hotels", [])
                for item in cursor:
                    entity = dict(booking_id=item['pid'], email=self.intent_obj.email)
                    actions = Lambda.fetch_actions("", entity=entity, intent_obj=self.intent_obj,
                                                   intent_list=[{'intent': self.intent_name}])
                    card = self.build_booking_card(item)
                    card.update({'actions': actions})
                    bookings_list.append(card)

                # for hotel in hotels:
                #     entity = dict(booking_id=hotel['hotel']['pid'], email=self.intent_obj.email)
                #     actions = Lambda.fetch_actions("", entity=entity, intent_obj=self.intent_obj,
                #                                    intent_list=[{'intent': self.intent_name}])
                #     card = self.build_booking_card(hotel['hotel'])
                #     card.update({'actions': actions})
                #     bookings_list.append(card)

                response['message'] = "Please select one of your recent bookings to view their cashback information"
                response['data']['items'] = bookings_list
                response['template'] = 'booking_info_list'

            except Exception as e:
                logger.error("EXCEPTION MESSAGE")

                logger.error(e)
                response['message'] = "Could not find booking information. Please contact CRM."
                response['success'] = True

        return response



        # else:

        #
        #     bookings = BookingMiddleware.get_user_booking_history(email=email, Pagination=5, verticals=vertical).json()
        #     eligible_booking = None
        #     flights = []
        #     hotels = []
        #     if vertical == "flights":
        #         flights = bookings["flight"]
        #     elif vertical == "hotels":
        #         hotels = bookings["hotels"]
        #     else:
        #         flights = bookings.get("flights", [])
        #         hotels = bookings.get("hotels", [])
        #     latest_date = None
        #     for hotel in hotels:
        #         if not latest_date or latest_date < datetime.strptime(hotel["hotel"]["bon"]["date"],
        #                                                               '%Y-%m-%d %H:%M:%S'):
        #             latest_date = datetime.strptime(hotel["hotel"]["bon"]["date"], '%Y-%m-%d %H:%M:%S')
        #             eligible_booking = hotel
        #
        #     for flight in flights:
        #         if not latest_date or latest_date < datetime.strptime(flight["flight"]["bon"]["date"],
        #                                                               '%Y-%m-%d %H:%M:%S'):
        #             latest_date = datetime.strptime(flight["flight"]["bon"]["date"], '%Y-%m-%d %H:%M:%S')
        #             eligible_booking = flight
        # if eligible_booking:
        #     pid = None
        #     latest_booking_info = None
        #     if eligible_booking.get("flight", None):
        #         pid = eligible_booking["flight"]["pid"]
        #         latest_booking_info = eligible_booking["flight"]
        #     elif eligible_booking.get("hotel", None):
        #         pid = eligible_booking["hotel"]["pid"]
        #         latest_booking_info = eligible_booking["hotel"]
        #
        #     if eligible_booking.get("gocash_processed", None) and eligible_booking["gocash_processed"] == 1:
        #         statement_found = False
        #         transactions = GocashMiddleware.get_transaction_details(pid)["txn_list"]
        #         for transaction in transactions:
        #             if transaction["txn_type"] == "promo" \
        #                     and transaction["promo_txn_amount"] == latest_booking_info["gocash_cash_back_value"]:
        #                 response.update({
        #                     "message": "For your booking id " + eligible_booking["id"] + " gocash of Rs. " \
        #                                + latest_booking_info["gocash_cash_back_value"] + " has been credited to " \
        #                                + "wallet."
        #                 })
        #                 statement_found = True
        #         if not statement_found:
        #             GocashMiddleware.credit_amount(vertical, pid, eligible_booking["email_id"],
        #                                            eligible_booking["user_id"],
        #                                            "promo", eligible_booking["gocash_cash_back_value"], 0, 0, {}, None)
        #             response.update({
        #                 "message": "We have credited gocash worth Rs. " + eligible_booking["gocash_cash_back_value"] \
        #                            + " to your wallet."
        #
        #             })
        #     else:
        #         response.update({
        #             "message": "Your latest booking with booking id " + eligible_booking["id"] + " is not eligible " \
        #                        + "for cashback."
        #         })
        # if "message" not in response:
        #     response.update({"message": "No booking found"})
        # return response

    def default_response(self):
        pass


intents.GoCashCashbackNotReceived.register_action(GoCashCashbackNotReceivedAction, "default")


class GiftNotReceivedAction(GoibiboAction):
    def __init__(self, **kwargs):
        super(GiftNotReceivedAction, self).__init__(**kwargs)
        self.nobooking = True
        self.intent_name = 'gocash.gift_not_received'
        self.sender_mobile = self.intent_obj.sender_mobile
        self.receiver_mobile = self.intent_obj.receiver_mobile
        self.retry_count = self.intent_obj.retry_count
        self.form_data = self.intent_obj.form_data
        super(GiftNotReceivedAction, self).__init__(**kwargs)

    def check_requirements(self):
        status = True
        resp = self.base_resp
        try:
            self.sender_mobile = self.form_data['sender_mobile']
            self.receiver_mobile = self.form_data['receiver_mobile']
            if not self.sender_mobile.isdigit() or not self.receiver_mobile.isdigit() or \
                    not len(self.receiver_mobile) == 10 or not len(self.sender_mobile) == 10:
                raise Exception
        except:
            self.retry_count += 1
            status = False
            resp = {
                'action': 'new_prompt',
                'template': 'md-text',
                'data':
                    {'form': {"fields":
                              [{'label': 'Sender\'s Mobile', 'type': "text", 'name': "sender_mobile"},
                               {'label': 'Receiver\'s Mobile', 'type': "text", 'name': "receiver_mobile"}],
                              'actionPayload': {'message': 'Check Gift Status', 'intent': 'gocash.gift_not_received',
                                                'entities': [{'retry_count': self.retry_count}]}},
                     'md-message': "Please provide the mobile number of the gift sender and receiver. "
                                   "Both fields are mandatory"},
                'next_intents': Lambda.fetch_actions("", entity={'user_email': self.intent_obj.email},
                                                     intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                  {'intent': "gocash.gocash_summary"},
                                                                  {'intent': "gocash.gocash_t&c"}],
                                                     intent_obj=self.intent_obj),
                'success': True,
            }
        # status = True
        # if not self.sender_mobile:
        #     resp['message'] = "Please provide the mobile number of the account which sent the gift:"
        #     resp['golambda_context'] = {
        #         'retry_count': self.retry_count + 1
        #     }
        #     status = False
        # elif not self.receiver_mobile:
        #     resp['message'] = "Please provide the mobile number of the account which was to receive the gift:"
        #     resp['golambda_context'] = {
        #         'retry_count': self.retry_count + 1,
        #         'sender_mobile': self.sender_mobile
        #     }
        #     status = False

        return resp, status

    def action(self):

        if self.retry_count > 2:
            return {"success": True}

        q_resp, check = self.check_requirements()
        if not check:
            return q_resp

        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'user_email': self.intent_obj.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_summary"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                              intent_obj=self.intent_obj)

        if not hasattr(self, 'sender_mobile') or not hasattr(self, 'receiver_mobile'):
            self.base_resp['data'] = {"message" :"Required params not provided"}
            self.base_resp['success'] = False
            logger.error("Params not provided")
            return self.base_resp

        gocash_response = GocashMiddleware.gift_details(self.sender_mobile, self.receiver_mobile)

        try:

            self.base_resp['success'] = gocash_response.status_code == 200
            if 'Message' in gocash_response.json():

                self.base_resp['message'] = gocash_response.json()['Message']
            else:
                raise Exception

        except:
            self.base_resp['success'] = False
            self.base_resp['message'] = 'Could not process your query due to technical errors'

        return self.base_resp

    def default_response(self):
        pass


intents.GiftNotReceived.register_action(GiftNotReceivedAction, "default")


class GocashBalanceAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.nobooking = True
        self.intent_name = 'gocash.balance'
        super(GocashBalanceAction, self).__init__(**kwargs)
        self.email = self.intent_obj.email
        # print self.user_email

    def action(self):
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={"user_email" : self.email},
                                                              intent_list=[{'intent': "gocash.gocash_summary"},
                                                                           {'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.how_to_earn_more"}],
                                                                           #{'intent': "gocash.gift_not_received"},],
                                                              intent_obj=self.intent_obj)

        logger.debug("In Gocash Balance Action")
        logger.debug(self.base_resp)

        if not hasattr(self, 'email') or not self.email:
            self.base_resp['data'] = {"message":"Required params not provided"}
            self.base_resp['success'] = False
            return self.base_resp

        gocash_response = GocashMiddleware.user_balance(self.email)

        try:
            if gocash_response.json().get('success'):
                resp_data = gocash_response.json()['data']
                """
                self.base_resp['message'] = 'Your GoCash balance is as below:' \
                                            '\n\tPromotional GoCash: %s' \
                                            '\n\tNon-Promotional Gocash: %s' \
                                            '\n\tTotal Gocash: %s' % (str(resp_data.get('p_amt', '0')),
                                                                      str(resp_data.get('np_amt', 0) +
                                                                          resp_data.get('b_amt', 0)),
                                                                      str(resp_data.get('t_amt', '0')))
                """
                self.base_resp['data'] = {"creditsBalance": resp_data.get('p_amt', '0'),
                                          "goCashPlusBalance": resp_data.get('b_amt', 0),
                                          "myCashBalance" : resp_data.get('np_amt', 0)
                                          }
                self.base_resp['template'] = "gocash_balance"
                self.base_resp['action'] = 'endWithResult'
            else:
                raise Exception
        except:
            self.base_resp['data'] = {"message":"User's Wallet Not Found"}
            self.base_resp['success'] = False

        return self.base_resp

    def default_response(self):
        pass

intents.GocashBalance.register_action(GocashBalanceAction, "default")


class GocashTandCAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.nobooking = True
        self.intent_name = "gocash.gocash_t&c"
        super(GocashTandCAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['template'] = 'md-text'
        self.base_resp['data']['md-message'] = "Please view the Terms and Conditions for goCash+ by " \
                                               "clicking on this [link](https://www.goibibo.com/gocash/)"

        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.balance"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass


intents.GocashTandC.register_action(GocashTandCAction, "default")


class GocashRedemptionAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.nobooking = True
        self.intent_name = 'gocash.how_to_redeem'
        super(GocashRedemptionAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "goCash+ is 100% redeemable on Flight, Hotel and Cab bookings."\
                                    "There are absolutely no usage restrictions"\
                                    "Use your goCash+ while making a booking"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.balance"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashRedemption.register_action(GocashRedemptionAction, "default")


class GocashSummaryAction(GoibiboAction):

    def __init__(self, **kwargs):
        self.intent_name = 'gocash.gocash_summary'
        super(GocashSummaryAction, self).__init__(**kwargs)
        self.user_email = self.intent_obj.email

    def action(self):

        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'user_email': self.user_email},
                                                              intent_list=[{'intent': "gocash.gocash_t&c"},
                                                                           #{'intent': "gocash.gocash_redemption"},
                                                                           {'intent': "gocash.how_to_redeem"}],
                                                              intent_obj=self.intent_obj)

        if not hasattr(self, 'email') or not self.user_email:
            self.base_resp['data'] = {"message":"Required params not provided"}
            self.base_resp['success'] = False
            return self.base_resp

        gocash_response = GocashMiddleware.user_summary(self.user_email)

        try:
            if gocash_response.status_code == 200:
                resp_data = gocash_response.json()
                self.base_resp['data'] = resp_data.get('results', '')

            else:
                raise Exception("wallet not found {}".format(gocash_response.json()))
        except Exception  as e:
            logger.error(" error in gocash_summary {}".format(str(e)))
            self.base_resp['data'] = {"message" :"User's Wallet Not Found"}
            self.base_resp['success'] = False

        return self.base_resp

    def default_response(self):
        pass

intents.GocashSummary.register_action(GocashSummaryAction, 'default')


class WhatIsGocashFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'whatis_gocash'
        super(WhatIsGocashFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "goCash is our travel booking currency which can be used to make bookings " \
                                    "with us at any point of time. " \
                                    "There are two types of goCash, namely Promotional goCash, " \
                                    "or goCash & goCashPlus." \
                                    "Promotional goCash can be earned by participating in various " \
                                    "promotional activities of Goibibo such as cash backs, referral and rewards. " \
                                    "Promotional goCash, also called goCash expires after 90 days from the date of issue."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "how_to_redeem"},
                                                                           #{'intent': "gocash.gocash_redemption"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.WhatIsGocashFAQ.register_action(WhatIsGocashFAQAction, "default")


class WhatIsGocashPlusFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'whatis_gocashplus'
        super(WhatIsGocashPlusFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "goCash+ is the travel currency at Goibibo."\
                                    "You can use 100% of your goCash+ without any restrictions."\
                                    "You can earn goCash+ through booking cashbacks, writing reviews,"\
                                    "referring friends and many more ways."\
                                    "goCash+ has a general validity of 3 calendar months"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.WhatIsGocashPlusFAQ.register_action(WhatIsGocashPlusFAQAction, "default")


class GocashPlusExpiryFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocashplus_expiry'
        super(GocashPlusExpiryFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "goCash+ earned from Cancellation has unlimited validity. It does not expire.\n" \
                                    "goCash+ earned from goContacts has validity of only 90 days from the date of issue."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashPlusExpiryFAQ.register_action(GocashPlusExpiryFAQAction, "default")


class GocashEarnFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_earn'
        super(GocashEarnFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "When you cancel your booking and choose refund as goCash+ option while cancelling " \
                                    "ticket, you will get goCash+/refund in your goibibo account. " \
                                    "You can also get goCash+ when a contact from your Phonebook transacts " \
                                    "on GoIbibo. You can ask your friend to gift goCash on your number but only " \
                                    "promotional goCash can be transferred. You can get goCash & goCashPlus through " \
                                    "the Referral program.For each invite, you get a certain amount of goCash. " \
                                    "Your friend also earns some amount, the bonus amount depending on the " \
                                    "promotional campaign. Cashbacks, Goibibo vouchers & Review bonuses are other ways " \
                                    "to get goCash. In case of any forgery, Goibibo has all rights to revert goCash " \
                                    "awarded to the user."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashEarnFAQ.register_action(GocashEarnFAQAction, "default")


class ReferralProgramFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'referral_program'
        super(ReferralProgramFAQAction, self).__init__(**kwargs)

    def action(self):
        message = "goCash+ referral program enables you and your friends to earn goCash+. " \
            "Your invitees will need to create a new Goibibo account by clicking the link you send them " \
            "via SMSFor each invite signing up, customers will get the bonus depending on the promotional campaign." \
            "When your friend books with Goibibo, you'll earn goCash+. " \
            "Your available goCash+ automatically appears on the My Account and Booking page. " \
            "If goCash+ isn't automatically added, it means booking does not qualify for the same." \
            "goCash+ expires in 90 days from the date it is issued. " \
            "People you refer will also see their goCash+ automatically appear on their account and booking page. " \
            "In case of any forgery, Goibibo has all rights to revert goCash+ awarded to the user."
        self.base_resp['message'] = message
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.ReferralProgramFAQ.register_action(ReferralProgramFAQAction, "default")


class GocashSafetyFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_safety'
        super(GocashSafetyFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "goCash+ is a very safe and encrypted payment instrument on Goibibo. Please keep " \
                                    "your email and password safe so that no one except you can use your goCash+. " \
                                    "In case of any fraudulent activity regarding your goCash+, please contact our " \
                                    "customer support services and we will take necessary actions to safeguard your interest."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashSafetyFAQ.register_action(GocashSafetyFAQAction, "default")


class GocashNotAvailableFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_not_available'
        super(GocashNotAvailableFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "You need to log into Goibibo account to view the goCash+ on the booking page."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashNotAvailableFAQ.register_action(GocashNotAvailableFAQAction, "default")


class GocashBalanceHowToFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_balance_how_to'
        super(GocashBalanceHowToFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "You can check goCash+ by signing into Goibibo website under My account or Mobile app."
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashBalanceHowToFAQ.register_action(GocashBalanceHowToFAQAction, "default")


class FraudReportingFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'fraud_reporting'
        super(FraudReportingFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "You can write to us visiting 24x7 goCare and provide us your email id and mobile " \
                                    "number with your concern. Your goCash+ will be blocked: " \
                                    "https://www.goibibo.com/support/"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"},
                                                                           # {'intent': "gocash.gocash_redemption"}
                                                                           ],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.FraudReportingFAQ.register_action(FraudReportingFAQAction, "default")


class GocashPromoLimitFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_promo_limit'
        super(GocashPromoLimitFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "The upper limit for earning goCash through promotional activities/refer and earn" \
                                    " is upto INR 10,000"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashPromoLimitFAQ.register_action(GocashPromoLimitFAQAction, "default")


class GocashPlusLimitFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_plus_limit'
        super(GocashPlusLimitFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "The upper limit for earning goCash+ in case of cancellation has no limit but " \
                                    "goCash+ earned through goContacts has a limit of 500"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.GocashPlusLimitFAQ.register_action(GocashPlusLimitFAQAction, "default")


class PromoBucketDifferenceFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'promo_bucket_difference'
        super(PromoBucketDifferenceFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = 'goCash+ doesn\'t have restriction or usage limits, whereas promotional GoCash ' \
                                    '(which is called simply "GoCash") has usage limits.'
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass

intents.PromoBucketDifferenceFAQ.register_action(PromoBucketDifferenceFAQAction, "default")


class GocashTransferFAQAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash_transfer'
        super(GocashTransferFAQAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = 'Gocash can be transfered to another account only through Gift gocash option ' \
                                    'through Mobile App (Android and IOS only)goCash+ and Non Promotional goCash+ ' \
                                    'cannot be transfered to another account'
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={'email': self.email},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"},
                                                                           {'intent': "gocash.balance"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass


class ReactUpgradeAction(GoibiboAction):
    def __init__(self,**kwargs):
        self.nobooking = True
        self.intent_name = "react.upgrade"
        super(ReactUpgradeAction, self).__init__(**kwargs)

    def action(self):
        message = "Hey, this is Gia, your personal travel advisor. I want to introduce myself to you with" \
                  " a reward of  300 goCash+. I hope you have an amazing travel experience with Goibibo."
        next_intent = [{
            "intent":"react.upgrade",
            "label":"Tap here to Claim",
            "message":"Tap here to Claim",
            "entities":{
                "user_id":self.user_id,
                "subIntent":"claim"
            }
        }]
        msg = Message(action='endWithResult', message=message, next_intents=next_intent)
        resp = Response()
        resp.add_message(msg)
        resp.update_success(True)
        return resp


class ReactUpgradeClaimAction(GoibiboAction):
    def __init__(self,**kwargs):
        self.nobooking =True
        self.intent_name = "react.upgrade"
        super(ReactUpgradeClaimAction, self).__init__(**kwargs)
        self.user_email = self.intent_obj.email

    def action(self):
        message = "Rupees 300 goCash+ is credited to your account"
        if not self.get_from_redis('react_gocash'):
            GocashMiddleware.credit_amount('promotional', "Gia", self.user_email, self.user_id, 'promo', 300, 0, 0, {})
        else:
            message = "You have already claimed your goCash+."
        self.save_in_redis('react_gocash', True,ttl=24*60*60*7)
        gocash_response = GocashMiddleware.user_balance(self.user_email)
        try:
            if gocash_response.json().get('success'):
                resp_data = gocash_response.json()['data']
                """
                self.base_resp['message'] = 'Your goCash+ balance is as below:' \
                                            '\n\tPromotional goCash+: %s' \
                                            '\n\tNon-Promotional goCash+: %s' \
                                            '\n\tTotal goCash+: %s' % (str(resp_data.get('p_amt', '0')),
                                                                      str(resp_data.get('np_amt', 0) +
                                                                          resp_data.get('b_amt', 0)),
                                                                      str(resp_data.get('t_amt', '0')))
                """
                self.base_resp['data'] = {"goCashBalance": resp_data.get('p_amt', '0'),
                                          "goCash+Balance": resp_data.get('np_amt', 0) \
                                                               + resp_data.get('b_amt', 0)
                                          }
                self.base_resp['template'] = "gocash_balance"
            else:
                raise Exception
        except Exception as e:
            self.base_resp['success'] = False
        msg = Message(action='endWithResult', message=message, data={"set_default_intents":False})
        resp = Response()
        resp.add_message(msg)
        self.base_resp['data']['set_default_intents'] = False
        msg2 = Message(**self.base_resp)
        resp.add_message(msg2)
        resp.update_success(True)
        return resp


class EarnMoreAction(GoibiboAction):
    def __init__(self, **kwargs):
        self.intent_name = 'gocash.how_to_earn_more'
        super(EarnMoreAction, self).__init__(**kwargs)

    def action(self):
        self.base_resp['message'] = "For more information on how to earn more goCash+, " \
                                    "click on the link [link](https://go.ibi.bo/IdDWcZyrDP)"
        self.base_resp['next_intents'] = Lambda.fetch_actions("", entity={},
                                                              intent_list=[{'intent': "gocash.how_to_redeem"},
                                                                           {'intent': "gocash.gocash_t&c"}],
                                                                           #{'intent': "gocash.gocash_redemption"}],
                                                              intent_obj=self.intent_obj)

        return self.base_resp

    def default_response(self):
        pass


class RefundNonPromoEligible(GoibiboAction):
    ELIGIBLE_URL = "http://gocash.goibibo.com/v1/load/npgc_refund_eligibility/"

    def __init__(self,**kwargs):
        super(RefundNonPromoEligible, self).__init__(**kwargs)
        self.intent_name = 'gocash.npgc_refund'
        self.email = self.intent_obj.email



    def action(self):
        try:

            resp = Response()
            message = Message()
            message.template = 'md_text_list'
            message.data = {}
            post_data = {
                "user_email": self.email
            }
            headers = {
                'Cache-Control': "no-cache",
                'Postman-Token': "4d4a4c40-8981-457e-b98e-3e2b0778d9cc"
            }
            response = requests.request("GET", self.__class__.ELIGIBLE_URL, headers=headers, params=post_data)
            #data = requests.get(self.__class__.ELIGIBLE_URL, data=post_data).json()
            #transactions = data['txn_list']
            tr_list =[]

            if response.json()['txn_list']:
                transactions = response.json()['txn_list']
                for txn in transactions:
                    tr = [{
                        "md_message": "**Transaction_date** :" + txn['Booking_date']+ " \n **Booking_ID** :" +
                                        txn['payment_txn_id'] + "\t **Amount** :" + str(txn['Refund_Amount'])
                                     ,
                        "actions": [{
                            "intent": "gocash.npgc_refund",
                            "entities": {
                                "txn_id": txn['payment_txn_id'],
                                "amount": str(txn['Refund_Amount']),
                                "subIntent": "complete"
                            },
                            "message": "Tap here to transfer",
                            "label": "Transfer"
                        }]
                    }]

                    message.action = "endWithResult"
                    tr_list.append(tr)
                message.next_intents = tr_list
                resp.add_message(message)
                resp.update_success(True)


            else:
                message.message = "You do not have any goCash+ eligible for refund."
                resp.add_message(message)
                resp.update_success(True)

            return resp

        except Exception as e:
            logger.error('gocash - Non promo refund eligible' + traceback.format_exc())
            message.message = "Error in extracting information. Contact the CRM team"
            resp.add_message(message)
            return resp




class RefundNonPromoComplete(GoibiboAction):

    REFUND_URL = "http://gocash.goibibo.com/v1/load/npgc_refund/"
    def __init__(self, **kwargs):
        self.intent_name = 'gocash.npgc_refund'
        super(RefundNonPromoComplete, self).__init__(**kwargs)
        self.txn_id = self.intent_obj.txn_id
        self.amount = self.intent_obj.amount

    def action(self):
        try:
            
            message = Message()

            resp = Response()
            data = {
                "txn_id": self.txn_id,
                "amount" : int(self.amount)
            }
            headers = {
                'Content-Type': "application/json",

                'Postman-Token': "ab14e811-70aa-4716-b68a-f4f43757d7f4"
            }

            response = requests.request("POST", self.__class__.REFUND_URL, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                message.message = "Transaction Successful! Amount will be credited to your account within 5-7 working days"
                resp.add_message(message)
                resp.update_success(True)
            else:
                message.message = "Error with refund! Please contact CRM"
                resp.add_message(message)
                resp.update_success(False)

            return resp

        except Exception as e:
            logger.error('gocash - Non promo refund complete' + traceback.format_exc())
            message.message = "Error with refund! Please contact CRM"
            resp.add_message(message)
            resp.update_success(False)
            return resp







intents.EarnMore.register_action(EarnMoreAction, "default")



#intents.GocashTransferFAQ.register_action(GocashTransferFAQAction, "default")
intents.GoCashLoadUPI.register_action(GoCashLoadUPI, "default")
intents.GoCashLoadUPI.register_action(GoCashLoadUPIInitiate, "initiate")
intents.GoCashLoadUPI.register_action(GoCashLoadUPIComplete, "complete")
ReactUpgrade.register_action(ReactUpgradeAction,'default')
ReactUpgrade.register_action(ReactUpgradeClaimAction,'claim')
intents.RefundNonPromo.register_action(RefundNonPromoEligible, 'default')

intents.RefundNonPromo.register_action(RefundNonPromoComplete, 'complete')