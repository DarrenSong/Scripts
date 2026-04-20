import datetime
import time
import os
import sys
import json

# 配置文件路径
CONFIG_FILE = "config.json"

def load_config():
    """从配置文件加载配置信息"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 转换日期格式
        for holiday in config["holidays"]:
            holiday["date"] = datetime.datetime.strptime(holiday["date"], "%Y-%m-%d").date()
        
        config["special_workdays"] = [
            datetime.datetime.strptime(d, "%Y-%m-%d").date() 
            for d in config["special_workdays"]
        ]
        
        # 转换工作时间配置
        work_schedule = config["work_schedule"]
        work_schedule["work_start"] = datetime.datetime.strptime(work_schedule["work_start"], "%H:%M").time()
        work_schedule["work_end"] = datetime.datetime.strptime(work_schedule["work_end"], "%H:%M").time()
        work_schedule["overtime_end"] = datetime.datetime.strptime(work_schedule["overtime_end"], "%H:%M").time()
        work_schedule["lunch_time"] = datetime.datetime.strptime(work_schedule["lunch_time"], "%H:%M").time()
        work_schedule["water_times"] = [
            datetime.datetime.strptime(t, "%H:%M").time() 
            for t in work_schedule["water_times"]
        ]
        
        return config
    
    except FileNotFoundError:
        print(f"错误：配置文件 {CONFIG_FILE} 未找到")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误：配置文件 {CONFIG_FILE} 格式不正确")
        sys.exit(1)
    except KeyError as e:
        print(f"配置项缺失: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"加载配置文件时出错: {str(e)}")
        sys.exit(1)

def is_workday(date, config):
    """
    判断给定日期是否为工作日
    考虑正常工作日（周一至周五）和特殊调班工作日
    """
    # 检查是否为特殊调班工作日（虽然是周末但需要上班）
    if date in config["special_workdays"]:
        return True
    
    # 正常工作日判断（周一至周五）
    return date.weekday() < 5

def calculate_time_difference(target_date):
    """计算当前日期与目标日期的天数差"""
    today = datetime.date.today()
    return (target_date - today).days

def format_timedelta(td):
    """将时间差格式化为小时+分钟+秒"""
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}小时{minutes}分钟{seconds}秒"

def get_work_status(weekday, current_time, config):
    """根据星期几和当前时间返回工作状态"""
    line1 = "大干办"
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    line2 = f"{weekdays[weekday]}大干" if weekday < 5 else "休息日"
    
    work_schedule = config["work_schedule"]
    current_time_only = current_time.time()
    
    if weekday < 5:
        if work_schedule["work_start"] <= current_time_only <= work_schedule["work_end"]:
            line3 = "工作时间\n"
        else:
            line3 = "非工作时间"
    else:
        line3 = "非工作时间"
    
    return ["\n" + line1, line2, line3]

def get_actual_payday(year, month, config):
    """
    获取实际发薪日（智能向前追溯）
    规则：如果基准日是非工作日，则向前追溯，直到找到最近的工作日
    考虑特殊调班工作日
    """
    base_day = config["payday_base"]
    
    # 从基准日开始向前追溯
    for day_offset in range(0, 8):  # 最多向前追溯7天
        check_day = base_day - day_offset
        if check_day < 1:  # 防止日期越界
            break
            
        candidate_date = datetime.date(year, month, check_day)
        
        # 检查是否为工作日（考虑特殊调班工作日）
        if is_workday(candidate_date, config):
            is_adjusted = (check_day != base_day)
            return candidate_date, is_adjusted, check_day
    
    return datetime.date(year, month, base_day), False, base_day

def get_payday_status(is_adjusted, actual_day, base_day):
    """判断发薪日状态"""
    if is_adjusted:
        return f"调整发薪日（原{base_day}号调整为{actual_day}号）"
    return "正常发薪日"

def get_next_water_reminder(current_time, config):
    """获取下一个喝水提醒时间"""
    work_schedule = config["work_schedule"]
    water_times = work_schedule["water_times"]
    
    # 如果当前时间已超过所有提醒时间，返回明天第一个提醒
    if current_time.time() > max(water_times):
        next_reminder = datetime.datetime.combine(
            current_time.date() + datetime.timedelta(days=1),
            min(water_times)
        )
        return "下一个提醒在明天", next_reminder
    
    # 查找下一个提醒时间
    for water_time in water_times:
        if current_time.time() < water_time:
            next_reminder = datetime.datetime.combine(
                current_time.date(),
                water_time
            )
            return "下一个喝水时间", next_reminder
    
    return "今日喝水提醒已完成", None

def main():
    try:
        # 加载配置
        config = load_config()
        work_schedule = config["work_schedule"]
        
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            now = datetime.datetime.now()
            weekday = now.weekday()
            weekdays_chinese = ["一", "二", "三", "四", "五", "六", "日"]
            
            # 界面显示
            print("-" * 60)
            print(" " * 15 + "节假日倒计时与健康提醒系统")
            print("-" * 60)
            
            print(f"当前时间：{now.strftime('%Y/%m/%d %H:%M:%S')}")
            print(f"星期：{weekdays_chinese[weekday]}")
            
            work_status = get_work_status(weekday, now, config)
            for status in work_status:
                print(status)
            
            # 发薪日计算
            today = datetime.date.today()
            payday, is_adjusted, actual_day = get_actual_payday(
                today.year, today.month, config
            )
            
            # 处理跨月逻辑
            if today > payday:
                next_month = today.month + 1
                next_year = today.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                payday, is_adjusted, actual_day = get_actual_payday(
                    next_year, next_month, config
                )
            
            payday_status = get_payday_status(
                is_adjusted, actual_day, config["payday_base"]
            )
            days_until_payday = (payday - today).days
            
            print(f"距离{payday.strftime('%m.%d')}发工资：{days_until_payday}天（{payday_status}）")
            
            # 显示特殊调班工作日信息（如果有）
            special_workdays_this_month = [
                d for d in config["special_workdays"] 
                if d.year == today.year and d.month == today.month
            ]
            if special_workdays_this_month:
                print("本月调班工作日：", end="")
                for i, swd in enumerate(special_workdays_this_month):
                    if i > 0:
                        print("、", end="")
                    print(f"{swd.day}号", end="")
                print()
            
            # 节假日倒计时
            print("\n节假日倒计时：")
            for holiday in config["holidays"]:
                days_left = calculate_time_difference(holiday["date"])
                if days_left >= 0:
                    print(f"距离 [{holiday['name']}\\{holiday['date'].strftime('%Y/%m/%d')}] {days_left}天（假期{holiday['vacation_days']}天）")
            
            # 健康提醒
            print("\n健康提醒设置：")
            print(f"午饭时间：{work_schedule['lunch_time'].strftime('%H:%M')}午餐时间")
            
            # 喝水提醒
            if is_workday(today, config):
                water_times_str = "、".join([t.strftime("%H:%M") for t in work_schedule["water_times"]])
                print(f"喝水时间：{water_times_str}（工作日）")
                
                # 显示下一个喝水提醒
                next_reminder_desc, next_reminder = get_next_water_reminder(now, config)
                if next_reminder:
                    time_diff = next_reminder - now
                    if time_diff.total_seconds() > 0:
                        print(f"{next_reminder_desc}: {next_reminder.strftime('%H:%M')} (还有{format_timedelta(time_diff)})")
            else:
                print("喝水时间：周末自由饮水")
            
            # 下班倒计时
            off_work = now.replace(
                hour=work_schedule["work_end"].hour,
                minute=work_schedule["work_end"].minute,
                second=0,
                microsecond=0
            )
            if now < off_work:
                print(f"距离下午{work_schedule['work_end'].strftime('%H:%M')}下班还有：{format_timedelta(off_work - now)}")
            else:
                print(f"距离下午{work_schedule['work_end'].strftime('%H:%M')}下班还有：已下班")
            
            # 加班倒计时
            overtime_end = now.replace(
                hour=work_schedule["overtime_end"].hour,
                minute=work_schedule["overtime_end"].minute,
                second=0,
                microsecond=0
            )
            if now < overtime_end:
                print(f"距离晚上{work_schedule['overtime_end'].strftime('%H:%M')}加班结束还有：{format_timedelta(overtime_end - now)}")
            else:
                print(f"距离晚上{work_schedule['overtime_end'].strftime('%H:%M')}加班结束还有：加班已结束")
            
            # 水印
            #watermark = now.strftime("%Y-%m-%d-%H:%M:%S")
            #print("\n" * 2 + " " * 5 + (watermark + " " * 3) * 10)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n系统已退出")
        sys.exit(0)

if __name__ == "__main__":
    main()
