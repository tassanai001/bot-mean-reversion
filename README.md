# 🚀 Mean Reversion Trading Bot - Production Ready

> **⚠️ IMPORTANT: Production-Ready Version Available!**
> 📦 **Use `bot_mean_reversion_production.py` for live trading**
> ✨ Includes: Leverage setup, position recovery, retry logic, safety mechanisms, and comprehensive logging
> 📖 **Read:** [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) | [`PRODUCTION_GUIDE.md`](PRODUCTION_GUIDE.md) | [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md)

**Bot สำหรับเทรดจริงบน Binance Futures**
**กลยุทธ์:** Z-Score Mean Reversion + ADX Filter
**Timeframe:** 1h (Optimized)

---

## 🆕 Production Version Features

The **production-ready version** (`bot_mean_reversion_production.py`) includes critical enhancements:

| Feature | Original Bot | Production Bot |
|---------|-------------|----------------|
| **Leverage Setup** | ❌ Manual | ✅ Automatic (10x) |
| **Margin Mode** | ❌ Manual | ✅ Automatic (ISOLATED) |
| **Position Recovery** | ❌ Lost on restart | ✅ Syncs from Binance |
| **Retry Logic** | ❌ None | ✅ 3 attempts + backoff |
| **Stop Loss Safety** | ❌ No fallback | ✅ Emergency close |
| **Logging** | ❌ print() | ✅ Rotating files |
| **Candle Timing** | ❌ Fixed 60s | ✅ Synced to candle close |
| **Precision** | ⚠️ Basic | ✅ Full Binance compliance |

**Quick Start:**
```bash
# 1. Update .env with new variables (see .env.example)
# 2. Run production bot
python bot_mean_reversion_production.py

# 3. Monitor logs
tail -f logs/bot_mean_reversion.log
```

**Documentation:**
- 📋 [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Complete overview
- 📖 [`PRODUCTION_GUIDE.md`](PRODUCTION_GUIDE.md) - Detailed feature guide
- 🔍 [`CODE_COMPARISON.md`](CODE_COMPARISON.md) - Original vs Production
- ⚡ [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md) - Quick lookup

---

## 📋 ข้อมูลพื้นฐาน

### **พารามิเตอร์ที่ใช้งาน (Optimized)**
- **Timeframe:** 1h
- **Z-Score Window:** 30
- **Entry Threshold:** ±2.5
- **Exit Threshold:** 0.0
- **ADX Threshold:** 30

### **ผลการทดสอบ (62 วัน)**
- **Return:** 3.52%
- **CAGR:** 22.58%
- **Sharpe Ratio:** 19.47
- **Win Rate:** 73.91%
- **Max Drawdown:** 3.30%
- **Total Trades:** 23

---

## 📁 โครงสร้างโปรเจค

```
bot-mean-reversion/
├── bot_mean_reversion.py    # ← Bot หลักสำหรับเทรดจริง
├── start.sh                  # ← สคริปต์เริ่มต้น Bot
├── .env                      # ← การตั้งค่า (API Keys, Parameters)
├── .env.example              # ← ตัวอย่างการตั้งค่า
├── venv/                     # ← Python virtual environment
└── archive/                  # ← ไฟล์ Backtest (เก็บไว้อ้างอิง)
    └── backtest_files/
```

---

## 🔧 การติดตั้ง

### **1. ติดตั้ง Dependencies**
```bash
# สร้าง virtual environment (ถ้ายังไม่มี)
python3 -m venv venv

# Activate
source venv/bin/activate

# ติดตั้ง packages
pip install ccxt pandas numpy python-dotenv
```

### **2. ตั้งค่า API Keys**
```bash
# คัดลอกไฟล์ตัวอย่าง
cp .env.example .env

# แก้ไข .env ใส่ API Keys ของคุณ
nano .env
```

**ใน `.env`:**
```bash
API_KEY=YOUR_BINANCE_API_KEY
API_SECRET=YOUR_BINANCE_SECRET_KEY
```

---

## 🚀 วิธีใช้งาน

### **วิธีที่ 1: ใช้สคริปต์ start.sh**
```bash
./start.sh
```

### **วิธีที่ 2: รันด้วยตัวเอง**
```bash
source venv/bin/activate
python bot_mean_reversion.py
```

---

## ⚙️ การตั้งค่า

### **ไฟล์ `.env`**

```bash
# ---------------------------------------------------------
# BINANCE API CREDENTIALS
# ---------------------------------------------------------
API_KEY=YOUR_BINANCE_API_KEY
API_SECRET=YOUR_BINANCE_SECRET_KEY

# ---------------------------------------------------------
# TRADING CONFIGURATION
# ---------------------------------------------------------
SYMBOL=BNB/USDT
TIMEFRAME=1h
LIMIT=1500

# ---------------------------------------------------------
# STRATEGY PARAMETERS (Optimized for 1h)
# ---------------------------------------------------------
Z_SCORE_WINDOW=30
ENTRY_THRESHOLD=2.5
EXIT_THRESHOLD=0.0
ADX_THRESHOLD=30

# ---------------------------------------------------------
# RISK MANAGEMENT
# ---------------------------------------------------------
RISK_PER_TRADE=0.01      # 1% ของ balance ต่อเทรด
STOP_LOSS_PCT=0.02       # 2% Stop Loss
MAX_LEVERAGE=10          # Leverage สูงสุด
```

---

## 📊 กลยุทธ์การเทรด

### **1. Z-Score Mean Reversion**
- คำนวณ Z-Score จากราคาปิด 30 แท่งเทียนล่าสุด
- เข้า Long เมื่อ Z-Score < -2.5 (ราคาต่ำกว่าค่าเฉลี่ยมาก)
- เข้า Short เมื่อ Z-Score > +2.5 (ราคาสูงกว่าค่าเฉลี่ยมาก)
- ออกเมื่อ Z-Score กลับสู่ 0 (ราคากลับสู่ค่าเฉลี่ย)

### **2. ADX Filter (Strategy Booster)**
- เข้าออเดอร์เฉพาะเมื่อ ADX < 30
- กรองออกช่วงที่ตลาดมีเทรนด์แรง
- ลดความเสี่ยงจากการเทรดในช่วงเทรนด์

### **3. Risk Management**
- Stop Loss: 2% จากราคาเข้า
- Position Size: 1% ของ balance ต่อเทรด
- Max Leverage: 10x

---

## ⚠️ คำเตือนสำคัญ

### **1. ทดสอบก่อนใช้เงินจริง**
- ✅ ทดสอบด้วย Paper Trading อย่างน้อย 1 เดือน
- ✅ เริ่มต้นด้วยเงินจำนวนเล็กน้อย
- ✅ ตรวจสอบผลลัพธ์ว่าสอดคล้องกับ Backtest

### **2. ความเสี่ยง**
- ⚠️ Sharpe Ratio 19.47 สูงมาก → อาจมี Overfitting
- ⚠️ Max Drawdown 3.30% → ต้องเตรียมพร้อมรับความเสี่ยง
- ⚠️ ทดสอบเพียง 62 วัน → อาจไม่ครอบคลุมทุกสภาวะตลาด

### **3. การจัดการความเสี่ยง**
- ❌ อย่าใช้เงินที่ไม่สามารถเสียได้
- ❌ อย่าใช้ Leverage สูงเกินไป
- ❌ อย่าลงทุนเกิน 5% ของ portfolio ในครั้งเดียว

---

## 📈 การติดตามผลลัพธ์

### **1. ตรวจสอบ Log**
Bot จะแสดง log การทำงาน:
- สัญญาณที่ตรวจพบ
- การเข้า/ออกออเดอร์
- PnL ของแต่ละเทรด

### **2. เปรียบเทียบกับ Backtest**
- ตรวจสอบว่า Win Rate ใกล้เคียง 73.91% หรือไม่
- ตรวจสอบว่า Return เป็นไปตามที่คาดหวังหรือไม่

### **3. ปรับปรุงพารามิเตอร์**
- ถ้าผลลัพธ์ไม่ดี → พิจารณา Re-optimize
- ถ้าตลาดเปลี่ยนแปลง → ปรับพารามิเตอร์ให้เหมาะสม

---

## 🔧 การแก้ไขปัญหา

### **ปัญหา: Bot ไม่เข้าออเดอร์**
- ตรวจสอบว่า ADX < 30 หรือไม่
- ตรวจสอบว่า Z-Score ถึง ±2.5 หรือไม่
- ลอง Paper Trading ก่อน

### **ปัญหา: API Error**
- ตรวจสอบ API Keys ใน `.env`
- ตรวจสอบว่าเปิด Futures Trading แล้วหรือไม่
- ตรวจสอบ IP Whitelist

### **ปัญหา: Position Size ผิดพลาด**
- ตรวจสอบ `RISK_PER_TRADE` ใน `.env`
- ตรวจสอบ Balance ใน Binance

---

## 📚 เอกสารอ้างอิง

### **Backtest Reports (เก็บใน archive/)**
- `OPTIMIZATION_1H_REPORT.md` - รายงานการ Optimization
- `optimization_1h_results.csv` - ผลลัพธ์ทั้งหมด 144 ชุด
- `1h_recommended_comparison.csv` - เปรียบเทียบ TOP 3

### **Backtest Scripts (เก็บใน archive/)**
- `backtest_mean_reversion.py` - สคริปต์ Backtest หลัก
- `optimize_1h.py` - สคริปต์ Optimization
- `multi_timeframe_backtest.py` - ทดสอบหลาย Timeframe

---

## 📞 การติดต่อ

หากมีปัญหาหรือข้อสงสัย:
1. ตรวจสอบ Log ของ Bot
2. อ่านเอกสารใน `archive/backtest_files/`
3. ทดสอบด้วย Paper Trading ก่อน

---

## 📝 Changelog

### **Version 1.0 (2026-01-17)**
- ✅ Optimize พารามิเตอร์สำหรับ Timeframe 1h
- ✅ ทดสอบกับข้อมูล 62 วัน
- ✅ Return 3.52%, Win Rate 73.91%
- ✅ พร้อมใช้งานจริง

---

## ⚖️ License

This project is for educational purposes only.
**Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.**

---

**สร้างโดย:** Antigravity AI
**วันที่:** 2026-01-17
**เวอร์ชัน:** 1.0 (Production Ready)
