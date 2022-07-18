import pulumi

import infrastructure

pulumi.export("url", infrastructure.customerdb_eip.public_ip)
pulumi.export("rds", infrastructure.customerdb_v8.address)
pulumi.export('bucket_name', infrastructure.bucket.id)
