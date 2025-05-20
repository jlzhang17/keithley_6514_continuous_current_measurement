import pyvisa
import time
import matplotlib.pyplot as plt
import statistics

GPIB_ADDRESS = 'GPIB0::14::INSTR'

rm = pyvisa.ResourceManager()

def collect_data(keithley, num_points):
    keithley.write("TRAC:CLE")
    keithley.write(f"TRAC:POIN {num_points}")
    keithley.write("TRAC:FEED SENS")
    keithley.write("TRAC:FEED:CONT NEXT")
    keithley.write("TRIG:SOUR IMM")
    keithley.write(f"TRIG:COUN {num_points}")
    keithley.write("INIT")
    time.sleep(2 + num_points * 0.1)  # 增加等待时间，防止数据未写入缓冲区

    raw_data = keithley.query("TRAC:DATA?")
    print("原始数据:", raw_data.strip()[:80] + '...')  # 显示前几项

    all_values = [float(x) for x in raw_data.strip().split(',')]
    current_values = all_values[::3]

    return current_values

try:
    voltage_input = input("请输入此次设置的电压值 (单位: V): ")
    
    keithley = rm.open_resource(GPIB_ADDRESS)
    keithley.write("*RST")
    keithley.write("*CLS")
    print("连接成功:", keithley.query("*IDN?").strip())

    # 设置测量参数
    keithley.write("FUNC 'CURR'")
    keithley.write("CURR:RANG 1E-8")     # 设置为10nA量程
    keithley.write("CURR:NPLC 10")        # 提高精度，抗干扰
    keithley.write("CURR:DAMP OFF")       # 禁用抑制，避免削弱信号

    # 零点校准
    keithley.write("SYST:ZCH ON")
    time.sleep(2)                         # 稳定等待
    keithley.write("SYST:ZCOR ON")        # 采集零点并开启修正
    keithley.write("SYST:ZCH OFF")

    all_current_values = []

    for _ in range(10):  # 每次采10点，共50点
        current_values = collect_data(keithley, 10)
        all_current_values.extend(current_values)

    # 去掉第一个点
    trimmed_values = all_current_values[1:]
    avg_current = sum(trimmed_values) / len(trimmed_values)
    sigma = statistics.stdev(trimmed_values)

    print(f"\n电压: {voltage_input} V")
    print(f"平均电流: {avg_current:.6e} A")
    print(f"标准差 (1σ): {sigma:.2e} A")

    # 写入数据文件
    with open("pyvisa_IV_6514.txt", "a") as f:
        f.write(f"{voltage_input}\t{avg_current:.6e}\t{sigma:.2e}\n")

    # 绘图
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, len(all_current_values) + 1), all_current_values, marker='o',
             label=f'Avg = {avg_current:.2e} A ± {sigma:.1e} A (1σ)')
    plt.title("Keithley 6514 - 50pts")
    plt.xlabel("Sample")
    plt.ylabel("Current (A)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

except Exception as e:
    print("通信失败:", str(e))

finally:
    try:
        keithley.close()
        rm.close()
    except:
        pass
