import unittest
import pulumi

class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        outputs = args.inputs
        if args.typ == "aws:ec2/instance:Instance":
            outputs = {
                **args.inputs,
                "publicIp": "1.2.3.4",
                "publicDns": "ec2-1-2-3-4.compute-1.amazonaws.com",
            }
        return [args.name + '_id', outputs]
    def call(self, args: pulumi.runtime.MockCallArgs):
        if args.token == "aws:ec2/getAmi:getAmi":
            return {
                "architecture": "x86_64",
                "id": "ami-0abcdef1234589",
            }
        return {}

pulumi.runtime.set_mocks(MyMocks())

# Now actually import the code that creates resources, and then test it.
import my_infra


# Test if port 443 for HTTPS is open.
@pulumi.runtime.test
def test_security_group_rules():
    def check_security_group_rules(args):
        urn, ingress = args
        https_exist = any([rule['from_port'] == 443 and any([block == "0.0.0.0/0" for block in rule['cidr_blocks']]) for rule in ingress])
        assert https_exist == True, f'HTTPS is not activated in security group {urn}'

    # Return the results of the unit tests.
    return pulumi.Output.all(my_infra.group.urn, my_infra.group.ingress).apply(check_security_group_rules)
