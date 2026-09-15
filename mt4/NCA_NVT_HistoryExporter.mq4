#property strict
#property script_show_inputs

// NVT research-only deep-history exporter.
// This script is intentionally separate from NCA_NormalRun_Exporter.
// It writes only to noda_draw\nvt_input and never modifies Normal Run input,
// NCA_DRAW__ objects, orders, positions, SL/TP, or any trading state.

input int BarsToExport = 6000;

string BASE_DIR = "noda_draw\\nvt_input";

string SafeSymbol(string value)
{
   string s = value;
   StringReplace(s, "\\", "_");
   StringReplace(s, "/", "_");
   StringReplace(s, ":", "_");
   StringReplace(s, "*", "_");
   StringReplace(s, "?", "_");
   StringReplace(s, "\"", "_");
   StringReplace(s, "<", "_");
   StringReplace(s, ">", "_");
   StringReplace(s, "|", "_");
   return s;
}

int DigitsForSymbol(string symbol)
{
   return (int)MarketInfo(symbol, MODE_DIGITS);
}

int ExportTF(string symbol, int tf, string tfName, datetime &firstTime, datetime &lastTime)
{
   int bars = iBars(symbol, tf);
   if(bars <= 2) return 0;

   int count = MathMin(BarsToExport, bars - 1); // shift 0 is forming/unclosed
   string path = BASE_DIR + "\\NVT_" + SafeSymbol(symbol) + "_" + tfName + ".csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
   {
      Print("NCA NVT HistoryExporter: FileOpen failed ", path, " err=", GetLastError());
      return -1;
   }

   FileWrite(h, "time","open","high","low","close","volume");
   int digits = DigitsForSymbol(symbol);
   int written = 0;
   firstTime = 0;
   lastTime = 0;

   for(int shift=count; shift>=1; shift--)
   {
      datetime t = iTime(symbol, tf, shift);
      if(t <= 0) continue;
      if(firstTime == 0) firstTime = t;
      lastTime = t;
      FileWrite(h,
         TimeToString(t, TIME_DATE|TIME_SECONDS),
         DoubleToString(iOpen(symbol,tf,shift), digits),
         DoubleToString(iHigh(symbol,tf,shift), digits),
         DoubleToString(iLow(symbol,tf,shift), digits),
         DoubleToString(iClose(symbol,tf,shift), digits),
         DoubleToString((double)iVolume(symbol,tf,shift), 0)
      );
      written++;
   }
   FileClose(h);
   return written;
}

void WriteStatus(
   string symbol,
   int d1, datetime d1First, datetime d1Last,
   int h4, datetime h4First, datetime h4Last,
   int h1, datetime h1First, datetime h1Last,
   int m15, datetime m15First, datetime m15Last)
{
   string path = BASE_DIR + "\\NVT_" + SafeSymbol(symbol) + "_export_status.csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   FileWrite(h,
      "exported_at","symbol","bars_requested","closed_bars_only","mode",
      "D1_count","D1_first","D1_last",
      "H4_count","H4_first","H4_last",
      "H1_count","H1_first","H1_last",
      "M15_count","M15_first","M15_last"
   );
   FileWrite(h,
      TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS),
      symbol,BarsToExport,"YES","NVT_RESEARCH_ONLY",
      d1,TimeToString(d1First,TIME_DATE|TIME_SECONDS),TimeToString(d1Last,TIME_DATE|TIME_SECONDS),
      h4,TimeToString(h4First,TIME_DATE|TIME_SECONDS),TimeToString(h4Last,TIME_DATE|TIME_SECONDS),
      h1,TimeToString(h1First,TIME_DATE|TIME_SECONDS),TimeToString(h1Last,TIME_DATE|TIME_SECONDS),
      m15,TimeToString(m15First,TIME_DATE|TIME_SECONDS),TimeToString(m15Last,TIME_DATE|TIME_SECONDS)
   );
   FileClose(h);
}

void OnStart()
{
   string symbol = Symbol();
   if(symbol == "")
   {
      Print("NCA NVT HistoryExporter: empty Symbol()");
      return;
   }
   if(BarsToExport < 100)
   {
      Print("NCA NVT HistoryExporter: BarsToExport must be >= 100");
      return;
   }

   FolderCreate("noda_draw", FILE_COMMON);
   FolderCreate(BASE_DIR, FILE_COMMON);

   datetime d1First=0,d1Last=0,h4First=0,h4Last=0,h1First=0,h1Last=0,m15First=0,m15Last=0;
   int d1 = ExportTF(symbol, PERIOD_D1, "D1", d1First, d1Last);
   int h4 = ExportTF(symbol, PERIOD_H4, "H4", h4First, h4Last);
   int h1 = ExportTF(symbol, PERIOD_H1, "H1", h1First, h1Last);
   int m15 = ExportTF(symbol, PERIOD_M15, "M15", m15First, m15Last);

   WriteStatus(symbol,
      d1,d1First,d1Last,
      h4,h4First,h4Last,
      h1,h1First,h1Last,
      m15,m15First,m15Last
   );

   Print("NCA NVT HISTORY EXPORT COMPLETE: ", symbol,
         " D1=", d1, " H4=", h4, " H1=", h1, " M15=", m15,
         " research_only=YES");
}
