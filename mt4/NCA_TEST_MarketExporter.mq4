#property strict

// NCA Live Draw v1 - TEST USDJPY closed-bar OHLC exporter.
// Attach to ONE chart in the TEST MT4 terminal only.
// No trading functions are used.

input string CanonicalSymbol = "USDJPY";
input string BrokerSymbol = "USDJPY#";
input int BarsToExport = 600;
input bool ExportImmediately = true;
input int TimerSeconds = 20;

string BASE_DIR = "noda_draw\\live_input";
datetime g_last_slot = 0;

int OnInit()
{
   SymbolSelect(BrokerSymbol, true);
   FolderCreate("noda_draw", FILE_COMMON);
   FolderCreate(BASE_DIR, FILE_COMMON);
   EventSetTimer(MathMax(5, TimerSeconds));
   if(ExportImmediately) ExportAll();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   datetime now = TimeLocal();
   int minute = TimeMinute(now);
   if(minute != 1 && minute != 16 && minute != 31 && minute != 46) return;

   datetime slot = now - TimeSeconds(now);
   if(slot == g_last_slot) return;
   g_last_slot = slot;
   ExportAll();
}

void ExportAll()
{
   int d1 = ExportTF(PERIOD_D1, "D1");
   int h4 = ExportTF(PERIOD_H4, "H4");
   int h1 = ExportTF(PERIOD_H1, "H1");
   int m15 = ExportTF(PERIOD_M15, "M15");
   WriteStatus(d1,h4,h1,m15);
   Print("NCA TEST MarketExporter: ", BrokerSymbol,
         " D1=",d1," H4=",h4," H1=",h1," M15=",m15);
}

int ExportTF(int tf, string tfName)
{
   int bars = iBars(BrokerSymbol, tf);
   if(bars <= 2) return 0;
   int count = MathMin(BarsToExport, bars - 1); // shift 0 is unclosed and excluded
   string path = BASE_DIR + "\\TEST_" + CanonicalSymbol + "_" + tfName + ".csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
   {
      Print("NCA TEST MarketExporter: FileOpen failed ", path, " err=", GetLastError());
      return 0;
   }
   FileWrite(h, "time","open","high","low","close","volume");
   int written = 0;
   for(int shift=count; shift>=1; shift--)
   {
      datetime t = iTime(BrokerSymbol, tf, shift);
      if(t <= 0) continue;
      FileWrite(h,
         TimeToString(t, TIME_DATE|TIME_SECONDS),
         DoubleToString(iOpen(BrokerSymbol,tf,shift), DigitsForSymbol()),
         DoubleToString(iHigh(BrokerSymbol,tf,shift), DigitsForSymbol()),
         DoubleToString(iLow(BrokerSymbol,tf,shift), DigitsForSymbol()),
         DoubleToString(iClose(BrokerSymbol,tf,shift), DigitsForSymbol()),
         DoubleToString((double)iVolume(BrokerSymbol,tf,shift), 0)
      );
      written++;
   }
   FileClose(h);
   return written;
}

int DigitsForSymbol()
{
   return (int)MarketInfo(BrokerSymbol, MODE_DIGITS);
}

void WriteStatus(int d1,int h4,int h1,int m15)
{
   string path = BASE_DIR + "\\TEST_" + CanonicalSymbol + "_export_status.csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   FileWrite(h,"exported_at","canonical_symbol","broker_symbol","D1","H4","H1","M15","closed_bars_only");
   FileWrite(h,TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS),CanonicalSymbol,BrokerSymbol,d1,h4,h1,m15,"YES");
   FileClose(h);
}
