#property strict
#property script_show_inputs

// Frozen 2026-09-19 eight-line reference viewer.
// Draws only the historical reference stored in NVT9_0919_REFERENCE_LINES_V01.
// It does not run Pivot/Candidate/Selector/Lifecycle logic.
// Audit ID: ID10IQ200

input bool ApplyToAllOpenTargetCharts = true;
input color D1TLColor = clrYellow;
input color D1CHColor = clrOrange;
input color H4TLColor = clrAqua;
input color H4CHColor = clrDeepSkyBlue;
input color H1TLColor = clrLime;
input color H1CHColor = clrGreen;
input color M15TLColor = clrMagenta;
input color M15CHColor = clrViolet;
input int LargeWidth = 2;
input int MidWidth = 1;
input int LabelFontSize = 8;

string PREFIX = "NVT9_REF0919__";
string PATH = "noda_draw\\live_output\\nvt9_reference_0919\\NVT9_0919_REFERENCE_DRAW.csv";

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

bool ReadHeader(int h)
{
   string h0=FileReadString(h), h1=FileReadString(h), h2=FileReadString(h);
   string h3=FileReadString(h), h4=FileReadString(h), h5=FileReadString(h);
   string h6=FileReadString(h), h7=FileReadString(h), h8=FileReadString(h);
   string h9=FileReadString(h), h10=FileReadString(h), h11=FileReadString(h), h12=FileReadString(h);
   return h0=="object_id" && h1=="symbol" && h2=="timeframe" &&
          h3=="structure_level" && h4=="role" && h5=="t1" && h6=="p1" &&
          h7=="t2" && h8=="p2" && h9=="generation_role" && h10=="generation" &&
          h11=="status" && h12=="extent";
}

bool ReadRow(int h,
   string &objectId,string &rowSymbol,string &rowTf,string &structure,string &role,
   string &t1s,string &p1s,string &t2s,string &p2s,string &genRole,
   string &generation,string &status,string &extent)
{
   if(FileIsEnding(h)) return false;
   objectId=FileReadString(h);
   if(objectId=="" && FileIsEnding(h)) return false;
   rowSymbol=FileReadString(h); rowTf=FileReadString(h); structure=FileReadString(h);
   role=FileReadString(h); t1s=FileReadString(h); p1s=FileReadString(h);
   t2s=FileReadString(h); p2s=FileReadString(h); genRole=FileReadString(h);
   generation=FileReadString(h); status=FileReadString(h); extent=FileReadString(h);
   return true;
}

bool SourceVisibleOnDestination(string sourceTf, string destTf)
{
   if(sourceTf == destTf) return true;
   if(sourceTf == "H4" && destTf == "D1") return true;
   if(sourceTf == "H1" && destTf == "H4") return true;
   if(sourceTf == "M15" && destTf == "H1") return true;
   return false;
}

void ColorsForTF(string tf, color &tl, color &ch)
{
   tl=D1TLColor; ch=D1CHColor;
   if(tf=="H4") { tl=H4TLColor; ch=H4CHColor; }
   else if(tf=="H1") { tl=H1TLColor; ch=H1CHColor; }
   else if(tf=="M15") { tl=M15TLColor; ch=M15CHColor; }
}

string RefIdFromObject(string objectId)
{
   int p=StringFind(objectId,"_SRC_",0);
   if(p>0) return StringSubstr(objectId,0,p);
   return objectId;
}

bool IsNVT9AuditOwnedObject(string name)
{
   if(StringFind(name,PREFIX,0)==0) return true;
   if(StringFind(name,"NVT9_TFMAP__",0)==0) return true;
   if(StringFind(name,"NVT9_PREVIEW__",0)==0) return true;
   if(StringFind(name,"NVT9_AB_CUTOFF__",0)==0) return true;
   return false;
}

void DeleteOwned(long chartId)
{
   int total=ObjectsTotal(chartId,-1,-1);
   for(int i=total-1;i>=0;i--)
   {
      string n=ObjectName(chartId,i,-1,-1);
      if(IsNVT9AuditOwnedObject(n)) ObjectDelete(chartId,n);
   }
}

int RenderOnChart(long chartId,string symbol,string tf)
{
   int h=FileOpen(PATH,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE) return -1;
   if(!ReadHeader(h)) { FileClose(h); return -2; }

   int rendered=0;
   while(!FileIsEnding(h))
   {
      string objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent;
      if(!ReadRow(h,objectId,rowSymbol,rowTf,structure,role,t1s,p1s,t2s,p2s,genRole,generation,status,extent)) break;
      if(rowSymbol!=symbol) continue;
      if(role=="HL") {
         if(rowTf!=tf) continue;
      } else {
         if(!SourceVisibleOnDestination(rowTf,tf)) continue;
      }

      datetime t1=StringToTime(t1s), t2=StringToTime(t2s);
      double p1=StrToDouble(p1s), p2=StrToDouble(p2s);
      if(t1<=0 || t2<=t1 || p1<=0 || p2<=0) continue;

      string name=PREFIX+objectId;
      if(StringLen(name)>63) continue;
      if(!ObjectCreate(chartId,name,OBJ_TREND,0,t1,p1,t2,p2)) continue;
      ObjectSetInteger(chartId,name,OBJPROP_RAY_RIGHT,true);
      ObjectSetInteger(chartId,name,OBJPROP_BACK,false);
      ObjectSetInteger(chartId,name,OBJPROP_SELECTABLE,false);

      color tlColor,chColor;
      ColorsForTF(rowTf,tlColor,chColor);
      color c=tlColor;
      int style=STYLE_SOLID;
      int width=(structure=="LARGE_DOW") ? LargeWidth : MidWidth;

      if(role=="HL")
      {
         c=tlColor;
         style=STYLE_DOT;
         width=2;
      }
      else if(role=="CH") c=chColor;
      else if(role=="TL_ZONE_EDGE" || role=="CH_ZONE_EDGE")
      {
         c=(role=="CH_ZONE_EDGE") ? chColor : tlColor;
         style=STYLE_DASH;
         width=1;
      }
      ObjectSetInteger(chartId,name,OBJPROP_COLOR,c);
      ObjectSetInteger(chartId,name,OBJPROP_STYLE,style);
      ObjectSetInteger(chartId,name,OBJPROP_WIDTH,width);
      rendered++;

      if(role=="TL" || role=="HL")
      {
         string refId=(role=="HL") ? objectId : RefIdFromObject(objectId);
         string lname=PREFIX+"LBL_"+refId;
         if(ObjectFind(chartId,lname)>=0) ObjectDelete(chartId,lname);
         if(ObjectCreate(chartId,lname,OBJ_TEXT,0,t2,p2))
         {
            ObjectSetText(lname,refId,LabelFontSize,"Arial",tlColor);
            ObjectSetInteger(chartId,lname,OBJPROP_SELECTABLE,false);
            ObjectSetInteger(chartId,lname,OBJPROP_BACK,false);
         }
      }
   }
   FileClose(h);
   ChartRedraw(chartId);
   return rendered;
}

bool ApplyOne(long chartId,string symbol)
{
   if(ChartSymbol(chartId)!=symbol) return false;
   int p=(int)ChartPeriod(chartId);
   if(!IsTargetPeriod(p)) return false;
   string tf=TFNameFromPeriod(p);
   DeleteOwned(chartId);
   int n=RenderOnChart(chartId,symbol,tf);
   Print("NVT9 0919 REF VIEW ",tf," objects=",n);
   return n>0;
}

void OnStart()
{
   int probe=FileOpen(PATH,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(probe==INVALID_HANDLE)
   {
      Print("NVT9 0919 REF VIEW STOP: reference CSV missing. Run PREPARE_NVT9_REFERENCE_0919.cmd");
      return;
   }
   FileClose(probe);

   string symbol=Symbol();
   int applied=0;
   if(!ApplyToAllOpenTargetCharts)
   {
      if(ApplyOne(ChartID(),symbol)) applied++;
   }
   else
   {
      long chartId=ChartFirst();
      int guard=0;
      while(chartId>=0 && guard<100)
      {
         if(ApplyOne(chartId,symbol)) applied++;
         chartId=ChartNext(chartId);
         guard++;
      }
   }
   Print("NVT9 0919 REF VIEW COMPLETE charts=",applied);
}
