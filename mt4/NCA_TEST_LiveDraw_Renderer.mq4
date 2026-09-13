#property strict
#property indicator_chart_window

// NCA Live Draw v1 TEST renderer.
// Reads a TEST snapshot from MT4 Common Files and draws only TL/CH/Zone edges.
// Colors/styles are display-only and carry no NODA semantic meaning.

input string BrokerSymbol = "USDJPY#";
input string SnapshotPath = "noda_draw\\live_output\\TEST_USDJPY_live_snapshot.csv";
input int RefreshSeconds = 5;
input color CurrentTLColor = clrAqua;
input color CurrentCHColor = clrDeepSkyBlue;
input color ZoneEdgeColor = clrSilver;
input color PreviousColor = clrDarkGray;
input int CurrentWidth = 2;
input int PreviousWidth = 1;

string PREFIX = "NCA_TEST__";

int OnInit()
{
   EventSetTimer(MathMax(2, RefreshSeconds));
   RenderSnapshot();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   RenderSnapshot();
}

int start()
{
   return(0);
}

string CurrentTFName()
{
   int p = Period();
   if(p == PERIOD_D1) return "D1";
   if(p == PERIOD_H4) return "H4";
   if(p == PERIOD_H1) return "H1";
   if(p == PERIOD_M15) return "M15";
   return "UNSUPPORTED";
}

void DeleteOwnedObjects()
{
   for(int i=ObjectsTotal()-1; i>=0; i--)
   {
      string n = ObjectName(i);
      if(StringFind(n, PREFIX, 0) == 0) ObjectDelete(n);
   }
}

void RenderSnapshot()
{
   if(Symbol() != BrokerSymbol) return;
   string tf = CurrentTFName();
   if(tf == "UNSUPPORTED") return;

   int h = FileOpen(SnapshotPath, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(h == INVALID_HANDLE)
   {
      // Fail-safe: missing snapshot does not erase the last valid drawing.
      return;
   }

   string h0 = FileReadString(h);
   for(int z=1; z<13 && !FileIsEnding(h); z++) FileReadString(h);
   if(h0 != "object_id")
   {
      FileClose(h);
      return;
   }

   DeleteOwnedObjects();
   int rendered = 0;
   while(!FileIsEnding(h))
   {
      string objectId = FileReadString(h);
      if(objectId == "" && FileIsEnding(h)) break;
      string canonical = FileReadString(h);
      string rowTf = FileReadString(h);
      string structure = FileReadString(h);
      string role = FileReadString(h);
      string t1s = FileReadString(h);
      string p1s = FileReadString(h);
      string t2s = FileReadString(h);
      string p2s = FileReadString(h);
      string genRole = FileReadString(h);
      string generation = FileReadString(h);
      string status = FileReadString(h);
      string extent = FileReadString(h);

      if(canonical != "USDJPY" || rowTf != tf) continue;
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
      color c = CurrentTLColor;
      int style = STYLE_SOLID;
      int width = CurrentWidth;
      if(previous)
      {
         c = PreviousColor;
         style = STYLE_DOT;
         width = PreviousWidth;
      }
      else if(role == "CH") c = CurrentCHColor;
      else if(role == "TL_ZONE_EDGE" || role == "CH_ZONE_EDGE")
      {
         c = ZoneEdgeColor;
         style = STYLE_DASH;
         width = 1;
      }
      ObjectSet(name, OBJPROP_COLOR, c);
      ObjectSet(name, OBJPROP_STYLE, style);
      ObjectSet(name, OBJPROP_WIDTH, width);
      rendered++;
   }
   FileClose(h);
   Comment("NCA TEST Live Draw | ", tf, " | objects=", rendered, " | no trade fields");
}
