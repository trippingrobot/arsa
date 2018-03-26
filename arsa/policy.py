class Policy(object):

    def __init__(self, event, allow=True, context=None):
        self.token = event['authorizationToken']
        self.arn = Policy.__get_resource_arn(event['methodArn'])

        # Set default principal_id to token
        self.principal_id = self.token
        self.allow = allow
        self.context = context

    @staticmethod
    def __get_resource_arn(arn):
        second_idx = arn.rfind('/', 0, arn.rfind('/'))
        return arn[:second_idx] + '/*/*'

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
