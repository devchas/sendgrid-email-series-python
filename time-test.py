from datetime import datetime, timedelta

today = datetime.today()
end_date = today + timedelta(days=10)
print end_date.strftime("%m/%d/%y")