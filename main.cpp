#include <iostream>
#include <fstream>
#include <wiringPi.h>
using namespace std;
#define defaultTemp 45
int getWantTemp()
{
	fstream setFile;
	setFile.open("TempSet.txt");
	if (!setFile.is_open())
	{
		setFile.open("TempSet.txt", ios::out | ios::app);
		if (!setFile.is_open())
	    {
		std::cout << "没有设置文件，创建一个！" << endl;
		setFile << "45" << endl;

		}else{
			cout << "文件无法写入！将使用默认值 " << defaultTemp << endl;

		}
		setFile.close();
		return defaultTemp;
		
	}
	int wantTemp;
	setFile >> wantTemp;
	setFile.close();
	return wantTemp;
}
void conTrolFan(bool on){
	if (on==1){
                digitalWrite(18,HIGH);
                cout<<"当前风扇状态"<<digitalRead(18)<<endl;
		// system("echo 1 > /sys/class/gpio/gpio18/value");
	}else{
                digitalWrite(18,LOW);
                cout<<"当前风扇状态"<<digitalRead(18)<<endl;
		// system("echo 0 > /sys/class/gpio/gpio18/value");
	}
}

int getTemp()
{
	ifstream tempFile;
	tempFile.open("/sys/class/thermal/thermal_zone0/temp");
	int temp;
	tempFile >> temp;
	tempFile.close();
	temp/=1000;
	return temp;
}

int main()
{
        wiringPiSetup();
        // pinMode(18, OUTPUT);
	// cout<<getWantTemp()<<getTemp()<<endl;
	int wantTemp = getWantTemp();
	//while (1)
	//{
		int temp = getTemp();
		if (temp > wantTemp)
		{
			conTrolFan(1);
		}
		else
		{
			conTrolFan(0);
		}
		std::cout << "当前温度：" << temp << "℃" << endl;
		std::cout <<"目标温度：" << wantTemp << "℃" << endl;
	    return 0;
	//}
}
