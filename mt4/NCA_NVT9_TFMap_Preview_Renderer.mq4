#property strict
#property script_show_inputs

// NVT9 research-only timeframe-mapped preview renderer.
// Reads NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv.
// Owns only NVT9_TFMAP__ objects and never touches Production NCA_DRAW__ or manual objects.
// No timer, no continuous polling, no trading functions.

input color PreviewTLColor = clrYellow;
input color PreviewCHColor = clrOrange;
input color PreviewZoneColor = clrViolet;
input color PreviewPreviousColor = clrDimGray;
input int PreviewCurrentWidth = 2;
input int PreviewPreviousWidth = 1;

string PREFIX = "NVT9_TFMAP__";
string BASE_DIR = "noda_draw\\live_output";

string CurrentTFName()
{
   int p = Period();
   if(p == PERIOD_D1) return "D1";
   if(p == PERIOD_H4) return "H4";
   if(p == PERIOD_H1) return "H1";
   if(p == PERIOD_M15) return "M15";
   return "UNSUPPORTED";
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

int CountRenderableRows(string path, string symbol, string tf)
{
   int h = FileOpen(path, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return -1;
   if(!ReadAndValidateHeader(h))
   {
      FileClose(h);
      return -2;
   }

   int count = 0;
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
      if(role != "TL" && role != "CH" && role != "TL_ZONE_EDGE" && role != "CH_ZONE_EDGE") continue;
      count++;
   }
   FileClose(h);
   return count;
}

void DeleteOwnedObjects()
{
   for(int i=ObjectsTotal()-1; i>=0; i--)
   {
      string n = ObjectName(i);
      if(StringFind(n, PREFIX, 0) == 0) ObjectDelete(n);
   }
}

int RenderRows(string path, string symbol, string tf)
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

      string name = PREFIX + objectId;
      if(!ObjectCreate(name, OBJ_TREND, 0, t1, p1, t2, p2)) continue;
      ObjectSet(name, OBJPROP_RAY, true);
      ObjectSet(name, OBJPROP_BACK, false);

      bool previous = (genRole == "PREVIOUS");
      color c = PreviewTLColor;
      int style = STYLE_SOLID;
      int width = PreviewCurrentWidth;
      if(previous)
      {
         c = PreviewPreviousColor;
         style = STYLE_DOT;
         width = PreviewPreviousWidth;
      }
      else if(role == "CH")
      {
         c = PreviewCHColor;
      }
      else if(role == "TL_ZONE_EDGE" || role == "CH_ZONE_EDGE")
      {
         c = PreviewZoneColor;
         style = STYLE_DASH;
         width = 1;
      }
      ObjectSet(name, OBJPROP_COLOR, c);
      ObjectSet(name, OBJPROP_STYLE, style);
      ObjectSet(name, OBJPROP_WIDTH, width);
      rendered++;
   }
   FileClose(h);
   return rendered;
}

void OnStart()
{
   string symbol = Symbol();
   string tf = CurrentTFName();
   if(tf == "UNSUPPORTED")
   {
      Print("NVT9 TFMap Renderer: unsupported chart timeframe.");
      return;
   }

   string path = BASE_DIR + "\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv";
   int ready = CountRenderableRows(path, symbol, tf);

   // D1 intentionally has no rows in this experiment. Do not erase anything there.
   if(tf == "D1" && ready <= 0)
   {
      Print("NVT9 TFMap Renderer: D1 intentionally has no mapped preview rows.");
      return;
   }

   if(ready <= 0)
   {
      Print("NVT9 TFMap Renderer: no valid mapped rows; keeping existing TFMap preview. code=", ready);
      return;
   }

   DeleteOwnedObjects();
   int rendered = RenderRows(path, symbol, tf);
   if(rendered < 0)
   {
      Print("NVT9 TFMap Renderer: render failure. code=", rendered);
      return;
   }

   ChartRedraw();
   Print("NVT9 TFMAP PREVIEW PASS: ", symbol, " ", tf, " objects=", rendered);
}
