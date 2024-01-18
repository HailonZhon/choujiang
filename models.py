# models.py
from tortoise import fields, models

class LotteryTicket(models.Model):
    id = fields.IntField(pk=True)
    ticket_code = fields.CharField(max_length=50, unique=True)
    result = fields.CharField(max_length=50, null=True)
    used = fields.BooleanField(default=False)
    use_count = fields.IntField(default=0)  # 新增字段，表示使用次数

class AdminUser(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=20, unique=True)
    password = fields.CharField(max_length=128)  # 直接存储明文密码

    @classmethod
    async def create_admin(cls):
        username = "hengliu123"
        password = "hengliu@123"
        existing_user = await cls.get_or_none(username=username)
        if existing_user is None:
            # 直接存储明文密码
            user = cls(username=username, password=password)
            print("创建账号密码成功！")
            await user.save()

    def verify_password(self, password):
        # 直接比较明文密码
        return self.password == password
