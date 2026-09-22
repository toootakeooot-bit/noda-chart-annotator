#property strict
#property script_show_inputs

// NVT9 OLD/NEW A-B audit viewer.
// Reads an already-built no-lookahead historical preview directly from
// Common\Files\noda_draw\live_output\nvt9_history_4w_0919\<case>\output.
// It does NOT overwrite the current live preview.
//
// One run can operate all open charts of the current symbol for
// D1/H4/H1/M15. It disables autoscroll, draws the historical preview,
// and moves each chart so the last bar before the case cutoff is at the
// right edge. A clearly visible vertical cut-off marker is drawn at the
// selected validation date on every target chart. Future bars remain in
// terminal history but are off-screen.

enum NVT9_AB_CASE
{
   CASE_20260912 = 0,
   CASE_20260919 = 1
};

enum NVT9_AB_VARIANT
{
   VARIANT_OLD = 0,
   VARIANT_NEW = 1
};

input NVT9_AB_CASE HistoryCase = CASE_20260912;
input NVT9_AB_VARIANT Variant = VARIANT_OLD;
input bool ApplyToAllOpenTargetCharts = true;
input bool AuditDeleteAllChartObjects = false;
input bool ShowCurrentStructuralOverlayOn0912Old = true;

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
input color CaseMarkerColor = clrWhite;
input int CaseMarkerWidth = 2;
input ENUM_LINE_STYLE CaseMarkerStyle = STYLE_DASH;

string PREFIX = "NVT9_TFMAP__";
string XPREFIX = "NVT9_X0912__";
string BASE_DIR = "noda_draw\\live_output\\nvt9_ab_0912_0919";
string OVERLAY_0912_PATH = "noda_draw\\live_output\\nvt9_reference_0912\\NVT9_0919_STRUCTURAL_OVERLAY.csv";

string CaseKey()
{
   if(HistoryCase == CASE_20260919) return "20260919";
   return "20260912";
}

string VariantKey()
{
   if(Variant == VARIANT_OLD) return "OLD";
   return "NEW";
}

datetime CaseCutoff()
{
   if(HistoryCase == CASE_20260919) return StringToTime("2026.09.19 00:00");
   return StringToTime("2026.09.12 00:00");
}

string HistoryPreviewPath()
{
   if(HistoryCase == CASE_20260912 && Variant == VARIANT_OLD)
      return "noda_draw\\live_output\\nvt9_reference_0912\\base\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv";
   return BASE_DIR + "\\" + CaseKey() + "\\" + VariantKey() +
          "\\output\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv";
}

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

int DeleteAuditOwnedObjects(long chartId)
{
   int deleted = 0;
   int total = ObjectsTotal(chartId, -1, -1);
   for(int i=total-1; i>=0; i--)
   {
      string n = ObjectName(chartId, i, -1, -1);
      if(n == "") continue;
      if(StringFind(n, PREFIX, 0) == 0 || StringFind(n, XPREFIX, 0) == 0 || StringFind(n, "NVT9_AB_CUTOFF__", 0) == 0)
      {
         if(ObjectDelete(chartId, n)) deleted++;
      }
   }
   return deleted;
}



bool DrawCaseMarker(long chartId, datetime cutoff)
{
   string name = "NVT9_AB_CUTOFF__" + CaseKey() + "__" + VariantKey();
   if(ObjectFind(chartId, name) >= 0)
      ObjectDelete(chartId, name);

   ResetLastError();
   if(!ObjectCreate(chartId, name, OBJ_VLINE, 0, cutoff, 0))
   {
      Print("NVT9 A-B VIEW: case marker create failed chart=", chartId,
            " cutoff=", TimeToString(cutoff, TIME_DATE|TIME_MINUTES),
            " err=", GetLastError());
      ResetLastError();
      return false;
   }

   ObjectSetInteger(chartId, name, OBJPROP_COLOR, CaseMarkerColor);
   ObjectSetInteger(chartId, name, OBJPROP_STYLE, CaseMarkerStyle);
   ObjectSetInteger(chartId, name, OBJPROP_WIDTH, CaseMarkerWidth);
   ObjectSetInteger(chartId, name, OBJPROP_BACK, false);
   ObjectSetInteger(chartId, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(chartId, name, OBJPROP_SELECTED, false);
   ObjectSetString(chartId, name, OBJPROP_TOOLTIP,
      "NVT9 A-B " + VariantKey() + " CUT-OFF " +
      TimeToString(cutoff, TIME_DATE|TIME_MINUTES));

   return true;
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


void ColorsForTF(string tf, color &tlColor, color &chColor)
{
   tlColor = D1TLColor;
   chColor = D1CHColor;
   if(tf == "H4") { tlColor = H4TLColor; chColor = H4CHColor; }
   else if(tf == "H1") { tlColor = H1TLColor; chColor = H1CHColor; }
   else if(tf == "M15") { tlColor = M15TLColor; chColor = M15CHColor; }
}

int RenderRowsOnChart(string path, long chartId, string symbol, string tf, datetime cutoff)
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

      ResetLastError();
      if(!ObjectCreate(chartId, name, OBJ_TREND, 0, t1, p1, t2, p2))
      {
         Print("NVT9 A-B VIEW: ObjectCreate failed chart=", chartId, " err=", GetLastError(), " name=", name);
         ResetLastError();
         continue;
      }

      bool clipAt0912 = (HistoryCase == CASE_20260912 && Variant == VARIANT_OLD);
      ObjectSetInteger(chartId, name, OBJPROP_RAY_RIGHT, !clipAt0912);
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
         style = STYLE_SOLID;
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


int RenderCurrentOverlay0912(long chartId,string symbol,string tf)
{
   if(!ShowCurrentStructuralOverlayOn0912Old) return 0;
   if(HistoryCase != CASE_20260912 || Variant != VARIANT_OLD) return 0;

   int h=FileOpen(OVERLAY_0912_PATH,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE) return 0;
   if(!ReadAndValidateHeader(h)) { FileClose(h); return -2; }

   int rendered=0;
   while(!FileIsEnding(h))
   {
      string objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent;
      if(!ReadRow(h,objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent)) break;
      if(rowSymbol!=symbol || rowTf!=tf) continue;

      datetime t1=StringToTime(t1s), t2=StringToTime(t2s);
      double p1=StrToDouble(p1s), p2=StrToDouble(p2s);
      if(t1<=0 || t2<=t1 || p1<=0 || p2<=0) continue;

      string name=XPREFIX+objectId;
      if(StringLen(name)>63) continue;
      if(!ObjectCreate(chartId,name,OBJ_TREND,0,t1,p1,t2,p2)) continue;
      ObjectSetInteger(chartId,name,OBJPROP_RAY_RIGHT,false);
      ObjectSetInteger(chartId,name,OBJPROP_BACK,false);
      ObjectSetInteger(chartId,name,OBJPROP_SELECTABLE,false);

      color tlColor,chColor;
      ColorsForTF(rowTf,tlColor,chColor);
      color c=tlColor;
      int style=STYLE_SOLID;
      int width=2;

      if(role=="CONT_TL") { c=tlColor; width=3; }
      else if(role=="CONT_CH") { c=chColor; width=2; }
      else if(role=="CONT_HL") { c=tlColor; style=STYLE_DASH; width=2; }
      else if(role=="MAJOR_TL") { c=D1TLColor; width=4; }
      else if(role=="MAJOR_CH") { c=D1CHColor; width=3; }
      else if(role=="MAJOR_HL") { c=D1TLColor; style=STYLE_DASH; width=2; }
      else if(role=="APPROVED_TL") { c=D1TLColor; width=4; }
      else if(role=="APPROVED_CH") { c=D1CHColor; width=3; }
      else if(role=="APPROVED_HL") { c=D1TLColor; style=STYLE_DASH; width=2; }
      else if(role=="REACTION_ZONE_LOW" || role=="REACTION_ZONE_HIGH") { c=H1TLColor; width=1; }
      else if(role=="UPDATED_CH") { c=H1CHColor; width=3; }

      ObjectSetInteger(chartId,name,OBJPROP_COLOR,c);
      ObjectSetInteger(chartId,name,OBJPROP_STYLE,style);
      ObjectSetInteger(chartId,name,OBJPROP_WIDTH,width);
      rendered++;

      if(role=="CONT_TL" || role=="CONT_HL" || role=="MAJOR_TL" || role=="MAJOR_HL" || role=="APPROVED_TL" || role=="APPROVED_HL" || role=="UPDATED_CH" || role=="REACTION_ZONE_HIGH")
      {
         string lname=XPREFIX+"LBL_"+objectId;
         if(ObjectFind(chartId,lname)>=0) ObjectDelete(chartId,lname);
         if(ObjectCreate(chartId,lname,OBJ_TEXT,0,t2,p2))
         {
            string labelText=objectId;
            if(role=="UPDATED_CH") labelText=objectId+" [UPDATED CH]";
            else if(role=="CONT_TL") labelText=objectId+" ["+rowTf+" CONT TL]";
            else if(role=="CONT_HL") labelText=objectId+" ["+rowTf+" DECISION HL]";
            else if(role=="MAJOR_TL") labelText=objectId+" [D1 MAJOR TL]";
            else if(role=="MAJOR_HL") labelText=objectId+" [D1 MAJOR HL]";
            else if(role=="APPROVED_TL") labelText=objectId+" [D1 APPROVED TL]";
            else if(role=="APPROVED_HL") labelText=objectId+" [D1 APPROVED HL]";
            else if(role=="REACTION_ZONE_HIGH") labelText=objectId+" [ZONE]";
            ObjectSetText(lname,labelText,8,"Arial",c);
            ObjectSetInteger(chartId,lname,OBJPROP_SELECTABLE,false);
            ObjectSetInteger(chartId,lname,OBJPROP_BACK,false);
         }
      }
   }
   FileClose(h);
   return rendered;
}


bool MoveChartToCase(long chartId, string symbol, int period, datetime cutoff)
{
   int shift = iBarShift(symbol, period, cutoff, false);
   if(shift < 0)
   {
      Print("NVT9 A-B VIEW: iBarShift failed chart=", chartId, " tf=", TFNameFromPeriod(period));
      return false;
   }

   ChartSetInteger(chartId, CHART_AUTOSCROLL, false);
   ChartSetInteger(chartId, CHART_SHIFT, true);

   // iBarShift is counted from the latest bar. Negative shift from CHART_END
   // moves the historical case bar to the right edge.
   bool ok = ChartNavigate(chartId, CHART_END, -shift);
   ChartRedraw(chartId);
   return ok;
}

bool ApplyHistoryToChart(long chartId, string symbol, string path, datetime cutoff)
{
   if(ChartSymbol(chartId) != symbol) return false;
   int period = (int)ChartPeriod(chartId);
   if(!IsTargetPeriod(period)) return false;

   string tf = TFNameFromPeriod(period);
   if(AuditDeleteAllChartObjects) DeleteAllChartObjects(chartId);
   else DeleteAuditOwnedObjects(chartId);

   int rendered = RenderRowsOnChart(path, chartId, symbol, tf, cutoff);
   int overlayRendered = RenderCurrentOverlay0912(chartId, symbol, tf);
   bool allowNoLine0912 = (HistoryCase == CASE_20260912 && Variant == VARIANT_OLD);
   if(rendered < 0)
   {
      Print("NVT9 A-B VIEW: preview read failed chart=", chartId, " tf=", tf, " code=", rendered);
      return false;
   }
   if(rendered == 0 && overlayRendered <= 0 && !allowNoLine0912)
   {
      Print("NVT9 A-B VIEW: no rows rendered chart=", chartId, " tf=", tf, " code=", rendered);
      return false;
   }
   if(rendered == 0 && allowNoLine0912)
   {
      Print("NVT9 A-B VIEW: 09/12 NO-LINE accepted chart=", chartId, " tf=", tf,
            " overlay=", overlayRendered);
   }

   if(!MoveChartToCase(chartId, symbol, period, cutoff))
   {
      Print("NVT9 A-B VIEW: navigation failed chart=", chartId, " tf=", tf);
      return false;
   }

   if(!DrawCaseMarker(chartId, cutoff))
   {
      Print("NVT9 A-B VIEW: case marker failed chart=", chartId, " tf=", tf);
      return false;
   }
   ChartRedraw(chartId);

   Print("NVT9 A-B VIEW PASS chart=", chartId, " tf=", tf, " case=", CaseKey(),
         " variant=", VariantKey(),
         " cutoff=", TimeToString(cutoff, TIME_DATE|TIME_MINUTES),
         " objects=", rendered, " overlay=", overlayRendered, " marker=YES");
   return true;
}

void OnStart()
{
   string symbol = Symbol();
   string path = HistoryPreviewPath();
   datetime cutoff = CaseCutoff();

   int probe = FileOpen(path, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(probe == INVALID_HANDLE)
   {
      Print("NVT9 A-B VIEW STOP: historical preview missing: ", path);
      Print("Run setup\\RUN_NVT9_AB_0912_0919.cmd first.");
      return;
   }
   FileClose(probe);

   int applied = 0;
   if(!ApplyToAllOpenTargetCharts)
   {
      if(ApplyHistoryToChart(ChartID(), symbol, path, cutoff)) applied++;
   }
   else
   {
      long chartId = ChartFirst();
      int guard = 0;
      while(chartId >= 0 && guard < 100)
      {
         if(ApplyHistoryToChart(chartId, symbol, path, cutoff)) applied++;
         chartId = ChartNext(chartId);
         guard++;
      }
   }

   Print("NVT9 A-B VIEW COMPLETE case=", CaseKey(), " variant=", VariantKey(),
         " charts=", applied,
         " cutoff=", TimeToString(cutoff, TIME_DATE|TIME_MINUTES));
}
