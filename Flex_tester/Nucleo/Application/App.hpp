/*
 * App.h
 *
 *  Created on: Mar 26, 2025
 *      Author: Igor
 */

#pragma once

#include "Board.hpp"
#include "ValveDetector.hpp"
#include "WaterMeterSimulator.hpp"
#include "Comm.hpp"
#include "CLIManager.h"
#include "RealTimer.hpp"
#include "DacControl.hpp"

class App
{
private:
	App();

public:
	static constexpr int VALVE_COUNT = 16;
	static constexpr int WM_SIM_COUNT = 5;

	static App &Instance() {
		static App _instance;
		return _instance;
	}

	Board &GetBoard() { return _board; }

	void Task();

private:
	Board _board;
	// TODO: UART to be defined
	//CLIManager _cli;
	Comm _comm;
	ValveDetector _valve[VALVE_COUNT];
	WaterMeterSimulator _wmSim[WM_SIM_COUNT];
	RealTimer _realTimer;
	DacControl _dac;

	void Init();
	bool CheckValves();
	void ControlWaterMeters(bool isValvesOpened);
	uint32_t GetValveBitmap() const;
	void HandleCommand(const BufferView<> &cmd);
	void AppendStatus(TextPrinter &p);
	bool LoadWmCyclesFromFlash(uint32_t (&wmCyclesMs)[WM_SIM_COUNT]);
	bool SaveWmCyclesToFlash();
};
