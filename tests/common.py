class MockTime:
    def __init__(self, init=0):
        self.time = 0
        self.mock = None

    def __call__(self):
        return self.time

    @classmethod
    def patch(cls, mocker, target):
        mock_time = cls()
        mock_time.mock = mocker.patch(target, side_effect=mock_time)
        return mock_time
