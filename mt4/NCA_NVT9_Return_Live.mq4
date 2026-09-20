#property strict
#property script_show_inputs

// Return from NVT9 historical audit view to the current NVT9 audit preview.
// The historical viewer reads its case file directly and never overwrites
// live_output\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv, so this script can
// restore the current preview, move charts to the latest bar, and re-enable
// autoscroll.

input bool ApplyToAllOpenTargetCharts = true;
input bool AuditDeleteAllChartObjects = true;

input color D1TLColor = clrYellow;
input color D1CHColor = clrOrange;
input color H4TLColor = clrAqua;
input color H4CHColor = clrDeepSkyBlue;
input color H1TLColor = clrLime;
input color H1CHColor = clrGreen;
input color M15TLColor = clrMagenta;
input color M15CHColor = clrViolet;
input int HLWidth = 2;
input int PreviewCurrentWidth = 2;
input int PreviewPreviousWidth = 1;

string PREFIX = "NVT9_TFMAP__";
string LIVE_PATH = "noda_draw\\live_output\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv";

string TFNameFromPeriod(int p)
{
   if(p == PERIOD_D1) return "D1";
   if(p == PERIOD_H4) return "H4";
   if(p == PERIOD_H1) return "H1";
   if(p == PERIOD_M15) return "M15";
   return "UNSUPPORTED";
}

bool IsTargetPeriod(int p)
{
   return (p == PERIOD_D1 || p == PERIOD_H4 || p == PERIOD_H1 || p == PERIOD_M15);
}

bool ReadAndValidateHeader(int h)
{
   string h0 = FileReadString(h);
   string h1 = FileReadString(h);
   string h2 = FileReadString(h);
   string h3 = FileReadString(h);
   string h4 = FileReadString(h);
   string h5 = FileReadString(h);
   string h6 = FileReadString(h);
   string h7 = FileReadString(h);
   string h8 = FileReadString(h);
   string h9 = FileReadString(h);
   string h10 = FileReadString(h);
   string h11 = FileReadString(h);
   string h12 = FileReadString(h);
   return h0 == "object_id" && h1 == "symbol" && h2 == "timeframe" &&
          h3 == "structure_level" && h4 == "role" && h5 == "t1" &&
          h6 == "p1" && h7 == "t2" && h8 == "p2" &&
          h9 == "generation_role" && h10 == "generation" &&
          h11 == "status" && h12 == "extent";
}

bool ReadRow(
   int h,
   string &objectId, string &rowSymbol, string &rowTf, string &structure,
   string &role, string &t1s, string &p1s, string &t2s, string &p2s,
   string &genRole, string &generation, string &status, string &extent
)
{
   if(FileIsEnding(h)) return false;
   objectId = FileReadString(h);
   if(objectId == "" && FileIsEnding(h)) return false;
   rowSymbol = FileReadString(h);
   rowTf = FileReadString(h);
   structure = FileReadString(h);
   role = FileReadString(h);
   t1s = FileReadString(h);
   p1s = FileReadString(h);
   t2s = FileReadString(h);
   p2s = FileReadString(h);
   genRole = FileReadString(h);
   generation = FileReadString(h);
   status = FileReadString(h);
   extent = FileReadString(h);
   return true;
}

int DeleteAllChartObjects(long chartId)
{
   int deleted = 0;
   int total = ObjectsTotal(chartId, -1, -1);
   for(int i=total-1; i>=0; i--)
   {
      string n = ObjectName(chartId, i, -1, -1);
      if(n == "") continue;
      if(ObjectDelete(chartId, n)) deleted++;
   }
   return deleted;
}

void SourceColors(string objectId, color &tlColor, color &chColor)
{
   bool isD1 = (StringFind(objectId, "SRC_D1_") >= 0);
   bool isH4 = (StringFind(objectId, "SRC_H4_") >= 0);
   bool isH1 = (StringFind(objectId, "SRC_H1_") >= 0);
   bool isM15 = (StringFind(objectId, "SRC_M15_") >= 0);

   tlColor = D1TLColor;
   chColor = D1CHColor;
   if(isH4) { tlColor = H4TLColor; chColor = H4CHColor; }
   else if(isH1) { tlColor = H1TLColor; chColor = H1CHColor; }
   else if(isM15) { tlColor = M15TLColor; chColor = M15CHColor; }
}

int RenderRowsOnChart(string path, long chartId, string symbol, string tf)
{
   int h = FileOpen(path, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return -1;
   if(!ReadAndValidateHeader(h))
   {
      FileClose(h);
      return -2;
   }

   int rendered = 0;
   while(!FileIsEnding(h))
   {
      string objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent;
      if(!ReadRow(h,objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent)) break;
      if(rowSymbol != symbol || rowTf != tf) continue;

      datetime t1 = StringToTime(t1s);
      datetime t2 = StringToTime(t2s);
      double p1 = StrToDouble(p1s);
      double p2 = StrToDouble(p2s);
      if(t1 <= 0 || t2 <= t1 || p1 <= 0 || p2 <= 0) continue;
      if(role != "TL" && role != "CH" && role != "TL_ZONE_EDGE" && role != "CH_ZONE_EDGE" && role != "HL") continue;

      string name = PREFIX + objectId;
      if(StringLen(name) > 63) continue;
      if(!ObjectCreate(chartId, name, OBJ_TREND, 0, t1, p1, t2, p2)) continue;

      ObjectSetInteger(chartId, name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(chartId, name, OBJPROP_BACK, false);

      color tlColor, chColor;
      SourceColors(objectId, tlColor, chColor);

      bool previous = (genRole == "PREVIOUS");
      color c = tlColor;
      int style = STYLE_SOLID;
      int width = PreviewCurrentWidth;
      if(role == "HL")
      {
         c = tlColor;
         width = HLWidth;
      }
      else if(previous)
      {
         c = (role == "CH") ? chColor : tlColor;
         style = STYLE_DOT;
         width = PreviewPreviousWidth;
      }
      else if(role == "CH")
      {
         c = chColor;
      }
      else if(role == "TL_ZONE_EDGE" || role == "CH_ZONE_EDGE")
      {
         c = tlColor;
         style = STYLE_DASH;
         width = 1;
      }

      ObjectSetInteger(chartId, name, OBJPROP_COLOR, c);
      ObjectSetInteger(chartId, name, OBJPROP_STYLE, style);
      ObjectSetInteger(chartId, name, OBJPROP_WIDTH, width);
      rendered++;
   }
   FileClose(h);
   return rendered;
}

bool ReturnChartLive(long chartId, string symbol)
{
   if(ChartSymbol(chartId) != symbol) return false;
   int period = (int)ChartPeriod(chartId);
   if(!IsTargetPeriod(period)) return false;

   if(AuditDeleteAllChartObjects) DeleteAllChartObjects(chartId);

   string tf = TFNameFromPeriod(period);
   int rendered = RenderRowsOnChart(LIVE_PATH, chartId, symbol, tf);
   if(rendered <= 0)
   {
      Print("NVT9 RETURN LIVE: current preview render failed chart=", chartId, " tf=", tf, " code=", rendered);
      return false;
   }

   ChartNavigate(chartId, CHART_END, 0);
   ChartSetInteger(chartId, CHART_AUTOSCROLL, true);
   ChartSetInteger(chartId, CHART_SHIFT, true);
   ChartRedraw(chartId);

   Print("NVT9 RETURN LIVE PASS chart=", chartId, " tf=", tf, " objects=", rendered);
   return true;
}

void OnStart()
{
   string symbol = Symbol();

   int probe = FileOpen(LIVE_PATH, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(probe == INVALID_HANDLE)
   {
      Print("NVT9 RETURN LIVE STOP: current preview missing: ", LIVE_PATH);
      Print("Run setup\\RUN_NVT9_TF_MAP_PREVIEW_0919.cmd first.");
      return;
   }
   FileClose(probe);

   int restored = 0;
   if(!ApplyToAllOpenTargetCharts)
   {
      if(ReturnChartLive(ChartID(), symbol)) restored++;
   }
   else
   {
      long chartId = ChartFirst();
      int guard = 0;
      while(chartId >= 0 && guard < 100)
      {
         if(ReturnChartLive(chartId, symbol)) restored++;
         chartId = ChartNext(chartId);
         guard++;
      }
   }

   Print("NVT9 RETURN LIVE COMPLETE charts=", restored);
}
