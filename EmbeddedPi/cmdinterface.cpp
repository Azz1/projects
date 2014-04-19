#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <math.h>
#include "arduPi.h"

typedef struct cmdframe{
    char CmdHeader;
    char CmdType;
    char CmdID;
    char Cmd;
    char DataLength;
    char CmdTail;
    char Data[0];
}CMDFRAME;

int debugmode = 1;

int TransReceProcess(struct cmdframe *cmd, int *length, char *buf)
{
    int i, len = 0;
    unsigned long counter = 0;
    char tmpBuf[200]={0};
    char offset = 1;

    Serial.write(cmd->CmdHeader);
    Serial.write(cmd->CmdType);
    Serial.write(cmd->CmdID);
    Serial.write(cmd->Cmd);
    Serial.write(cmd->DataLength);
    for(i = 0; i < cmd->DataLength; i++)
    {
        Serial.write(cmd->Data[i]);
    }
    Serial.write(cmd->CmdTail);

    while(!Serial.available())
    {
        counter++;
        delay(5);
        if(counter > 2000)
            return (-1); 
    }
    Serial.readBytes(tmpBuf, 300);

    len = tmpBuf[2+offset];
    for(i=0;i<len;i++)
      *(buf+i) = tmpBuf[3+i+offset];
    
    *(buf+len) = '\0';
    if((tmpBuf[0+offset] == 0xc9) || (tmpBuf[1+offset] == 0xa3)) {
        *length = len;
        return 1;
    }
    if((tmpBuf[0+offset] == 0xb6) || (tmpBuf[1+offset] == 0xdc)) {
        *length = len;
        return 0;
    }   

    return (-1);
}

void printcmd(const char *name, struct cmdframe *cmd)
{
  int i;
  if(debugmode) {
    printf("%s cmd is ", name);
    printf("%x %x %x %x %x ",cmd->CmdHeader,cmd->CmdType,cmd->CmdID,cmd->Cmd,cmd->DataLength);
    for(i=0; i<cmd->DataLength;i++) printf("%d ", cmd->Data[i]);
    printf("%x\n", cmd->CmdTail);
  }
}

#define N 5

int InitEmbeddedPi() 
{
    int state, len;
    char RxBuf[50];

    Serial.begin(115200);
    delay(100);

    struct cmdframe *pCmd;
    pCmd = (struct cmdframe*)malloc(200);

    pCmd->CmdHeader = 0xa5;
    pCmd->CmdTail = 0x5a;

    pCmd->CmdType = 0x40;
    pCmd->CmdID = 0x00;
    pCmd->Cmd = 0x05;
    pCmd->DataLength = 0;
    state = TransReceProcess(pCmd, &len, RxBuf);
    if(debugmode) printf("epi init returns [%d]\n", state);
    free(pCmd);
    return state;
}

extern "C" {

double ReadMR()
{
    int state, len;
    double MeasureValue = -1, average = 0.0;
    char RxBuf[50];

    InitEmbeddedPi();

    struct cmdframe *pCmd;
    pCmd = (struct cmdframe*)malloc(200);

    pCmd->CmdHeader = 0xa5;
    pCmd->CmdTail = 0x5a;

    // Init MR
    pCmd->CmdID = 4;
    pCmd->DataLength = 0;
    pCmd->Cmd = 1;
    state = TransReceProcess(pCmd,&len,RxBuf);
    if(!state) {if(debugmode) printf("Execution error, please try again\n"); }
    else if(state < 0) {if(debugmode) printf("Receive timeout,please try again\n");}
    else if(state > 0) {if(debugmode) printf("Magnetic Field Sensor init ok\n");}

    // Start MR
    pCmd->Cmd = 2;
    state = TransReceProcess(pCmd,&len,RxBuf);
    if(!state) {if(debugmode) printf("Execution error, now try again\n");}
    if(state < 0) {if(debugmode) printf("Receive timeout, now try again\n");}
    if(state > 0) { 
        average = 0;
        for(int j = 0; j < N; j++) {
            MeasureValue = 0;
            for(int i = 0; i < len; i++) MeasureValue += RxBuf[i] << (8*i);
            average += MeasureValue;
            TransReceProcess(pCmd,&len,RxBuf);
        }
        MeasureValue = average / N - 160;
	if(MeasureValue < 0)
	    MeasureValue += 360;
    }

    // Stop MR
    pCmd->Cmd = 3;
    state = TransReceProcess(pCmd,&len,RxBuf);
    if(!state) { if(debugmode) printf("Execution error, please try again\n"); }
    else if(state < 0) {if(debugmode) printf("Receive timeout,please try again\n");}
    else if(state > 0) {if(debugmode) printf("Magnetic Field Sensor stop ok\n");} 

    free(pCmd);
    return MeasureValue;
}


double ReadDistance()
{
    InitEmbeddedPi();

    int state, len;
    double MeasureValue = -1, average = 0.0, voltage = 0.0;
    char RxBuf[50];

    struct cmdframe *pCmd;
    pCmd = (struct cmdframe*)malloc(200);

    pCmd->CmdHeader = 0xa5;
    pCmd->CmdTail = 0x5a;

    // Start IR
    pCmd->CmdID = 1;
    pCmd->DataLength = 1;
    pCmd->Data[0] = 0;	//AINPin
    pCmd->Cmd = 3;
    state = TransReceProcess(pCmd,&len,RxBuf);
    if(!state) { if(debugmode) printf("Execution error, please try again\n"); }
    else if(state < 0) {if(debugmode) printf("Receive timeout,please try again\n");}
    else if(state > 0) { 
        MeasureValue = 0;
        average = 0;
        for(int j = 0; j < N; j++) {
            MeasureValue = 0;
            for(int i = 0; i < len; i++) MeasureValue += RxBuf[i] << (8*i);
            average += MeasureValue;
            TransReceProcess(pCmd,&len,RxBuf);
        }
        MeasureValue = average / N;
        voltage = (MeasureValue * 3300.0 / 4095);
        if(debugmode) printf("voltage(mV) = %.2f\n",voltage);
    }

    free(pCmd);
    return MeasureValue;
}

}

int main(int argc, char *argv[])
{
  double value;

  if(argc == 1) {
    char InputNum;
    debugmode = 1;

    while(1){ 
	InputNum = 0;
        printf("Select the demo you want to run\n");
        printf("1.Magnetic Field Sensor Demo\n");
        printf("2.AD Measurement Demo\n");
        printf("q.Quit\n");
        scanf("%d",&InputNum);
        if(InputNum == 1) {
            value = ReadMR();
	    printf("Direction = %.2f\n\n", value);
	    continue;
        } else if(InputNum == 2){
	    value = ReadDistance();
	    printf("Distance = %.2f\n\n", value);
            continue; 
        } else {
            printf("quit\n");
            break;
  	}

    }
  } else {
    debugmode = 0;
    if(strcmp(argv[1], "m") == 0) {
        value = ReadMR();
	printf("%.2f", value);
    } else if(strcmp(argv[1], "d") == 0) {
        value = ReadDistance();
	printf("%.2f", value);
    }
  }

  return 0;
}
