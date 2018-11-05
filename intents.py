from golambda.Intent import Intent, Attribute
from golambda.Lambda import Lambda
from email.utils import parseaddr



class GoCashLoadUPI(Intent):
    _registry = {}

    email = Attribute(value_type=unicode, IsMandatory=True)
    mobile = Attribute(value_type=unicode, IsMandatory=True)
    paymentid = Attribute(value_type=unicode, IsMandatory=False)

    amount = Attribute(
        value_type=list,
        IsMandatory=False,
        default_value=[],
        path='inhouse_entities.cardinal'
    )

    callback_data = Attribute(
        value_type=dict,
        IsMandatory=False,
        path='callback_data',
        default_value={}

    )

    def validation(self):
        return "Please provide a valid VPA"

    def get_message(self):
        return "Load Money into your GoCash Wallet"

    def get_label(self):
        return "Load Gocash"


class GoCashCashbackNotReceived(Intent):
    _registry = {}

    email = Attribute(value_type=unicode, IsMandatory=True)
    booking_id = Attribute(value_type=unicode, IsMandatory=False, path='pid')

    def validation(self):
        pass

    def get_message(self):
        return "Gocash Cashback not received"

    def get_label(self):
        return "Gocash Cashback not received"


class GiftNotReceived(Intent):
    _registry = {}
    form_data = Attribute(
        value_type=dict,
        IsMandatory=False,
        path='form_data',
        default_value={}
    )
    sender_mobile = Attribute(value_type=unicode, IsMandatory=False)
    receiver_mobile = Attribute(value_type=unicode, IsMandatory=False)
    retry_count = Attribute(value_type=int, IsMandatory=False,default_value=0)

    def validation(self):
        return True
        # return self.sender_mobile.isdigit() and self.receiver_mobile.isdigit() and len(self.sender_mobile) ==10 \
        #        and len(self.receiver_mobile) == 10

    def get_message(self):
        return "Gift Not Received"


class GocashBalance(Intent):
    _registry = {}
    user_email = Attribute(value_type=unicode, IsMandatory=True, path="email")


    def validation(self):
        return len(parseaddr(self.email)[1]) > 0

    def get_message(self):
        return "goCash+ Balance"

class GocashTandC(Intent):
    _registry = {}

    def validation(self):
        pass

    def get_message(self):
        return "Gocash T&C"


class GocashRedemption(Intent):
    _registry = {}

    def validation(self):
        pass

    def get_message(self):
        return "How to Redeem goCash+"


class GocashSummary(Intent):
    _registry = {}

    user_email = Attribute(value_type=unicode, IsMandatory=True, path = "email")

    def validation(self):
        return len(parseaddr(self.user_email)[1]) > 0

    def get_message(self):
        return "Gocash Summary"

class WhatIsGocashFAQ(Intent):
    _registry = {}

    def validation(self):
        pass

    def get_message(self):
        return "What Is GoCash"

class WhatIsGocashPlusFAQ(Intent):
    _registry = {}

    def validation(self):
        pass

    def get_message(self):
        return "What Is goCash+"


class GocashPlusExpiryFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashEarnFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class ReferralProgramFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashSafetyFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashNotAvailableFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashBalanceHowToFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class FraudReportingFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashPromoLimitFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashPlusLimitFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class PromoBucketDifferenceFAQ(Intent):
    _registry = {}

    def validation(self):
        pass


class GocashTransferFAQ(Intent):
    _registry = {}

    def validation(self):
        pass

class ReactUpgrade(Intent):
    _registry = {}

    def validation(self):
        pass

class EarnMore(Intent):
    _registry = {}

    def validation(self):
        pass

    def get_message(self):
        return "How to earn more goCash+"

class RefundNonPromo(Intent):
    _registry = {}
    txn_id = Attribute(value_type=unicode, IsMandatory=False, path = "txn_id")
    amount = Attribute(value_type=unicode, IsMandatory=False, path = "amount")

    def validation(self):
        pass



Lambda.register("react.upgrade", ReactUpgrade)
Lambda.register("gocash.cashback_not_received", GoCashCashbackNotReceived)
Lambda.register("gocash.gift_not_received", GiftNotReceived)
#Lambda.register("gocash_balance", GocashBalance)
Lambda.register("gocash.balance", GocashBalance)
Lambda.register("gocash.how_to_redeem", GocashRedemption)
Lambda.register("gocash.gocash_t&c", GocashTandC)
#Lambda.register("gocash.gocash_redemption", GocashRedemption)
Lambda.register("gocash.gocash_summary", GocashSummary)
#Lambda.register("gocash.whatis_gocash", WhatIsGocashFAQ)
Lambda.register("gocash.whatis_gocashplus", WhatIsGocashPlusFAQ)
Lambda.register("gocash.gocashplus_expiry", GocashPlusExpiryFAQ)
#Lambda.register("gocash.gocash_earn", GocashEarnFAQ)
Lambda.register("gocash.referral_program", ReferralProgramFAQ)
Lambda.register("gocash.gocash_safety", GocashSafetyFAQ)
Lambda.register("gocash.gocash_not_available", GocashNotAvailableFAQ)
Lambda.register("gocash.gocash_balance_how_to", GocashBalanceHowToFAQ)
Lambda.register("gocash.fraud_reporting", FraudReportingFAQ)
#Lambda.register("gocash.gocash_promo_limit", GocashPromoLimitFAQ)
Lambda.register("gocash.gocash_plus_limit", GocashPlusLimitFAQ)
#Lambda.register("gocash.promo_bucket_difference", PromoBucketDifferenceFAQ)
#Lambda.register("gocash.gocash_transfer", GocashTransferFAQ)
Lambda.register("gocash.load_wallet", GoCashLoadUPI)
Lambda.register("gocash.how_to_earn_more", EarnMore)
Lambda.register("gocash.npgc_refund", RefundNonPromo)

