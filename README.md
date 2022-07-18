# Modern Cloud Infrastructure with AWS and Pulumi

This is a companion github repository for the Oreilly live training [Modern Cloud Infrastructure with AWS and Pulumi](https://learning.oreilly.com/live-events/modern-cloud-infrastructure-with-aws-and-pulumi/0636920074622/0636920074621/)

# Install Pulumi
https://www.pulumi.com/docs/get-started/install/
 
# Export you AWS credentials
```bash
export AWSAccessKeyId=<your AWS Access Key Id>
export AWSSecretKey=<your AWS Secret Key>
```

# Generates Key pair
```bash
ssh-keygen -f customerdb-keypair
```

# Setup dev-2 environment
``` bash
pulumi stack init dev-2
...

# confirgure global config
pulumi config set env_name dev_2
pulumi config set aws:region us-east-1

# Condigure RDS config
pulumi config set dbName customerdb
pulumi config set dbUsername admin
pulumi config set dbPassword s0meth1ngA32s0me2 --secret
pulumi config set dbInstanceSize db.t3.small

# Configure EC2 config
pulumi config set ec2InstanceSize t3.small
pulumi config set publicKeyPath customerdb-keypair.pub
pulumi config set privateKeyPath customerdb-keypair
```

# Connect to the remote EC2 node, install MySQL client and connect to the RDS MySQL database.
```bash
ssh -i customerdb-keypair ec2-user@<ip of the EC2 node>

# Install mysql client on the EC2 node
sudo yum install mysql

# Connect to mysql from the EC2 node
mysql -h <dns_name of the RDS database> -P 3306 -u admin -p
```
