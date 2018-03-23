class Policy(object):

    def __init__(self, principal_id, arn, allow=True, context=None):
        self.principal_id = principal_id
        self.arn = arn
        self.allow = allow
        self.context = context

    def as_dict(self):
        return {
            'principalId': self.principal_id,
            'policyDocument': {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": ('Allow' if self.allow else 'Deny'),
                        "Resource": self.arn
                    }
                ]},
            'context': self.context
        }
