#property strict
#property script_show_inputs

// NCA Normal Run v1 - one-shot closed-bar exporter.
// Run this script on the XM MT4 chart you want to rebuild/draw.
// The exact MT4 Symbol() value is the canonical symbol identity.
// No timer, no continuous monitoring, no trading functions.

input int BarsToExport = 600;

string BASE_DIR = "noda_draw\\live_input";

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

int ExportTF(string symbol, int tf, string tfName)
{
   int bars = iBars(symbol, tf);
   if(bars <= 2) return 0;

   int count = MathMin(BarsToExport, bars - 1); // shift 0 is unclosed
   string path = BASE_DIR + "\\NORMAL_" + SafeSymbol(symbol) + "_" + tfName + ".csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
   {
      Print("NCA NormalRun Exporter: FileOpen failed ", path, " err=", GetLastError());
      return -1;
   }

   FileWrite(h, "time","open","high","low","close","volume");
   int digits = DigitsForSymbol(symbol);
   int written = 0;
   for(int shift=count; shift>=1; shift--)
   {
      datetime t = iTime(symbol, tf, shift);
      if(t <= 0) continue;
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

void WriteStatus(string symbol, int d1, int h4, int h1, int m15)
{
   string path = BASE_DIR + "\\NORMAL_" + SafeSymbol(symbol) + "_export_status.csv";
   int h = FileOpen(path, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   FileWrite(h,"exported_at","symbol","D1","H4","H1","M15","closed_bars_only","mode");
   FileWrite(h,TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS),symbol,d1,h4,h1,m15,"YES","NORMAL_RUN");
   FileClose(h);
}

void OnStart()
{
   string symbol = Symbol();
   if(symbol == "")
   {
      Print("NCA NormalRun Exporter: empty Symbol()");
      return;
   }

   FolderCreate("noda_draw", FILE_COMMON);
   FolderCreate(BASE_DIR, FILE_COMMON);

   int d1 = ExportTF(symbol, PERIOD_D1, "D1");
   int h4 = ExportTF(symbol, PERIOD_H4, "H4");
   int h1 = ExportTF(symbol, PERIOD_H1, "H1");
   int m15 = ExportTF(symbol, PERIOD_M15, "M15");
   WriteStatus(symbol, d1, h4, h1, m15);

   Print("NCA NORMAL RUN EXPORT COMPLETE: ", symbol,
         " D1=", d1, " H4=", h4, " H1=", h1, " M15=", m15);
}
