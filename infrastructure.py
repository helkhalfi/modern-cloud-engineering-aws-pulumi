import pulumi
import pulumi_aws as aws
from pulumi_aws import s3
import pulumi_awsx as awsx

config = pulumi.Config()

# Environment name
env_name = config.require("env_name")
# A path to the EC2 keypair's public key:
public_key_path = config.require("publicKeyPath")
# A path to the EC2 keypair's private key:
private_key_path = config.require("privateKeyPath")
# The customer database size:
db_instance_size = config.get("dbInstanceSize") or "db.t3.small"
# The customer database name:
db_name = config.get("dbName") or "customerdb"
# The customer database user's name:
db_username = config.get("dbUsername") or "admin"
# The customer database user's password:
db_password = config.require_secret("dbPassword")
# The customer EC2 instance's size:
ec2_instance_size = config.get("ec2InstanceSize") or "t3.small"


# Dynamically fetch AZs so we can spread across them.
availability_zones = aws.get_availability_zones()
# Dynamically query for the Amazon Linux 2 AMI in this region.
aws_linux_ami = aws.ec2.get_ami(owners=["amazon"],
    filters=[aws.ec2.GetAmiFilterArgs(
        name="name",
        values=["amzn2-ami-hvm-*-x86_64-ebs"],
    )],
    most_recent=True)


# Read in the public key for easy use below.
public_key = open(public_key_path).read()
# Read in the private key for easy use below (and to ensure it's marked a secret!)
private_key = pulumi.Output.secret(open(private_key_path).read())


### VPC ###
vpc = aws.ec2.Vpc(f"{env_name}-vpc",
    cidr_block="10.192.0.0/16",
    enable_dns_support=True, 
    enable_dns_hostnames=True,
    enable_classiclink=False,
    instance_tenancy="default")

# Create public subnets for the EC2 instance.
subnet_public1 = aws.ec2.Subnet(f"{env_name}-subnet-public-1",
    vpc_id=vpc.id,
    cidr_block="10.192.0.0/24",
    map_public_ip_on_launch=True,
    availability_zone=availability_zones.names[0])

# Create 2 private subnets for RDS:
subnet_private1 = aws.ec2.Subnet(f"{env_name}-subnet-private-1",
    vpc_id=vpc.id,
    cidr_block="10.192.20.0/24",
    map_public_ip_on_launch=False,
    availability_zone=availability_zones.names[1])

subnet_private2 = aws.ec2.Subnet(f"{env_name}-subnet-private-2",
    vpc_id=vpc.id,
    cidr_block="10.192.21.0/24",
    map_public_ip_on_launch=False,
    availability_zone=availability_zones.names[2])

# Create a gateway for internet connectivity:
igw = aws.ec2.InternetGateway(f"{env_name}-igw", vpc_id=vpc.id)

# Create a route table:
public_rt = aws.ec2.RouteTable(f"{env_name}-public-rt",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        # associated subnets can reach anywhere:
        cidr_block="0.0.0.0/0",
        # use this IGW to reach the internet:
        gateway_id=igw.id,
    )])
rta_public_subnet1 = aws.ec2.RouteTableAssociation(f"{env_name}-rta-public-subnet-1",
    subnet_id=subnet_public1.id,
    route_table_id=public_rt.id)

## Create S3-buckets
bucket = s3.Bucket(f"bucket-{env_name}")

## Security Groups
# Security group for EC2:
ec2_allow_rule = aws.ec2.SecurityGroup(f"{env_name}-ec2-allow-rule",
    vpc_id=vpc.id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTPS",
            from_port=443,
            to_port=443,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP",
            from_port=80,
            to_port=80,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="SSH",
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
    )],
    tags={
        "Name": "allow ssh,http,https",
    })

# Security group for RDS:
rds_allow_rule = aws.ec2.SecurityGroup(f"{env_name}-rds-allow-rule",
    vpc_id=vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        description="MySQL",
        from_port=3306,
        to_port=3306,
        protocol="tcp",
        security_groups=[ec2_allow_rule.id],
    )],
    # allow all outbound traffic.
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
    )],
    tags={
        "Name": "allow ec2",
    })


## EC2 and RDS
# Place the RDS instance into private subnets:
rds_subnet_grp = aws.rds.SubnetGroup(f"{env_name}-rds-subnet-grp", subnet_ids=[
    subnet_private1.id,
    subnet_private2.id,
])

# Create the RDS instance:
customerdb_v8 = aws.rds.Instance(f"{env_name}-customerdb",
    allocated_storage=20,
    engine="mysql",
    engine_version="8.0.29",
    instance_class=db_instance_size,
    db_subnet_group_name=rds_subnet_grp.id,
    vpc_security_group_ids=[rds_allow_rule.id],
    db_name=db_name,
    username=db_username,
    password=db_password,
    skip_final_snapshot=True)

# Create a keypair to access the EC2 instance:
customerdb_keypair = aws.ec2.KeyPair(f"{env_name}-customerdb-keypair", public_key=public_key)


# Create an EC2 instance to run customer (after RDS is ready).
customerdb_instance = aws.ec2.Instance(f"{env_name}-customerdb-instance",
    ami=aws_linux_ami.id,
    instance_type=ec2_instance_size,
    subnet_id=subnet_public1.id,
    vpc_security_group_ids=[ec2_allow_rule.id],
    key_name=customerdb_keypair.id,
    tags={
        "Name": "customer.web",
    },
    # Only create after RDS is provisioned.
    opts=pulumi.ResourceOptions(depends_on=[customerdb_v8]))

# Give our EC2 instance an elastic IP address.
customerdb_eip = aws.ec2.Eip(
    f"{env_name}-customerdb-eip",
     instance=customerdb_instance.id
)
