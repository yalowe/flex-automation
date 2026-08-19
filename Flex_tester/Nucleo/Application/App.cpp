/*
 * App.cpp
 *
 *  Created on: Mar 26, 2025
 *      Author: Igor
 */

#include "App.hpp"
#include "cmsis_os.h"
#include "gpio.h"
#include "TextScanner.hpp"
#include "TextPrinter.hpp"
#include "stm32l4xx_hal_flash.h"

namespace {
	constexpr uint32_t kWmPersistMagic = 0x574D4346U;       // "WMCF"
	constexpr uint32_t kWmPersistVersion = 1U;
	constexpr uint32_t kWmDefaultCycleMs = 1000U;
	constexpr uint32_t kWmPersistAddress = 0x080FF800U;     // last 2KB page in 1MB flash

	struct WmPersistBlob {
		uint32_t magic;
		uint32_t version;
		uint32_t cyclesMs[App::WM_SIM_COUNT];
		uint32_t checksum;
	};

	uint32_t ComputeChecksum(const WmPersistBlob &blob)
	{
		uint32_t sum = blob.magic ^ blob.version;
		for (int i = 0; i < App::WM_SIM_COUNT; ++i) {
			sum ^= blob.cyclesMs[i] + (0x9E3779B9U * (uint32_t)(i + 1));
		}
		return sum;
	}
}

App::App():
	_comm { _board._commUart },
	_valve {
		{ ._port = VALVE_0_GPIO_Port, ._pin = VALVE_0_Pin, ._id = 1, ._activeLow = false },
		//{ ._port = GPIOC, ._pin = GPIO_PIN_13, ._id = 1, ._activeLow = false }, // PC13 (Active High)
		{ ._port = VALVE_1_GPIO_Port, ._pin = VALVE_1_Pin, ._id = 2, ._activeLow = false },
		{ ._port = VALVE_2_GPIO_Port, ._pin = VALVE_2_Pin, ._id = 3, ._activeLow = false },
		{ ._port = VALVE_3_GPIO_Port, ._pin = VALVE_3_Pin, ._id = 4, ._activeLow = false },
		{ ._port = VALVE_4_GPIO_Port, ._pin = VALVE_4_Pin, ._id = 5, ._activeLow = false },
		{ ._port = VALVE_5_GPIO_Port, ._pin = VALVE_5_Pin, ._id = 6, ._activeLow = false },
		{ ._port = VALVE_6_GPIO_Port, ._pin = VALVE_6_Pin, ._id = 7, ._activeLow = false },
		{ ._port = VALVE_7_GPIO_Port, ._pin = VALVE_7_Pin, ._id = 8, ._activeLow = false },
		{ ._port = VALVE_8_GPIO_Port, ._pin = VALVE_8_Pin, ._id = 9, ._activeLow = false },
		{ ._port = VALVE_9_GPIO_Port, ._pin = VALVE_9_Pin, ._id = 10, ._activeLow = false },
		{ ._port = VALVE_10_GPIO_Port, ._pin = VALVE_10_Pin, ._id = 11, ._activeLow = false },
		{ ._port = VALVE_11_GPIO_Port, ._pin = VALVE_11_Pin, ._id = 12, ._activeLow = false },
		{ ._port = VALVE_12_GPIO_Port, ._pin = VALVE_12_Pin, ._id = 13, ._activeLow = false },
		{ ._port = VALVE_13_GPIO_Port, ._pin = VALVE_13_Pin, ._id = 14, ._activeLow = false },
		{ ._port = VALVE_14_GPIO_Port, ._pin = VALVE_14_Pin, ._id = 15, ._activeLow = false },
		{ ._port = VALVE_15_GPIO_Port, ._pin = VALVE_15_Pin, ._id = 16, ._activeLow = false },
	},
	_wmSim {
		//{ ._port = WM_SIM_0_GPIO_Port, ._pin = WM_SIM_0_Pin, ._id = 1 },
		{ ._port = LD2_GPIO_Port, ._pin = LD2_Pin, ._id = 1 }, // LED for testing on evaluation board
		{ ._port = WM_SIM_1_GPIO_Port, ._pin = WM_SIM_1_Pin, ._id = 2 },
		{ ._port = WM_SIM_2_GPIO_Port, ._pin = WM_SIM_2_Pin, ._id = 3 },
		{ ._port = WM_SIM_3_GPIO_Port, ._pin = WM_SIM_3_Pin, ._id = 4 },
		{ ._port = WM_SIM_4_GPIO_Port, ._pin = WM_SIM_4_Pin, ._id = 5 },
	}
{}

void App::Init()
{
	uint32_t wmCyclesMs[WM_SIM_COUNT] = {
		kWmDefaultCycleMs,
		kWmDefaultCycleMs,
		kWmDefaultCycleMs,
		kWmDefaultCycleMs,
		kWmDefaultCycleMs,
	};
	LoadWmCyclesFromFlash(wmCyclesMs);

	for (auto &valve: _valve) {
		valve.Init();
	}

	for (int i = 0; i < WM_SIM_COUNT; ++i) {
		auto &wm = _wmSim[i];
		wm.SetStatus(WaterMeterSimulator::Status::Triggered, wmCyclesMs[i]);
	}

	_realTimer.Set(0,0,0);
	
	_dac.Init();
	_dac.SetVoltage(0.0f);
}

bool App::LoadWmCyclesFromFlash(uint32_t (&wmCyclesMs)[WM_SIM_COUNT])
{
	const auto *blob = reinterpret_cast<const WmPersistBlob*>(kWmPersistAddress);
	if (blob->magic != kWmPersistMagic || blob->version != kWmPersistVersion) {
		return false;
	}

	WmPersistBlob tmp = *blob;
	if (tmp.checksum != ComputeChecksum(tmp)) {
		return false;
	}

	for (int i = 0; i < WM_SIM_COUNT; ++i) {
		uint32_t value = blob->cyclesMs[i];
		if (value == 0U || value > 600000U) {
			return false;
		}
		wmCyclesMs[i] = value;
	}

	return true;
}

bool App::SaveWmCyclesToFlash()
{
	WmPersistBlob blob {};
	blob.magic = kWmPersistMagic;
	blob.version = kWmPersistVersion;
	for (int i = 0; i < WM_SIM_COUNT; ++i) {
		uint32_t cycle = _wmSim[i]._cycleTimeMs;
		blob.cyclesMs[i] = (cycle > 0U) ? cycle : kWmDefaultCycleMs;
	}
	blob.checksum = ComputeChecksum(blob);

	uint32_t existingCycles[WM_SIM_COUNT] = {};
	if (LoadWmCyclesFromFlash(existingCycles)) {
		bool isSame = true;
		for (int i = 0; i < WM_SIM_COUNT; ++i) {
			if (existingCycles[i] != blob.cyclesMs[i]) {
				isSame = false;
				break;
			}
		}
		if (isSame) {
			return true;
		}
	}

	FLASH_EraseInitTypeDef eraseInit {};
	uint32_t pageError = 0U;
	eraseInit.TypeErase = FLASH_TYPEERASE_PAGES;
	eraseInit.Banks = FLASH_BANK_2;
	eraseInit.Page = 255U;
	eraseInit.NbPages = 1U;

	if (HAL_FLASH_Unlock() != HAL_OK) {
		return false;
	}

	HAL_StatusTypeDef status = HAL_FLASHEx_Erase(&eraseInit, &pageError);
	if (status == HAL_OK) {
		const uint64_t *src = reinterpret_cast<const uint64_t*>(&blob);
		for (uint32_t offset = 0; offset < sizeof(WmPersistBlob); offset += sizeof(uint64_t)) {
			status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, kWmPersistAddress + offset, *src++);
			if (status != HAL_OK) {
				break;
			}
		}
	}

	HAL_FLASH_Lock();
	return status == HAL_OK;
}

uint32_t App::GetValveBitmap() const
{
	uint32_t bitmap = 0;
	for (int i = 0; i < VALVE_COUNT; ++i) {
		if (_valve[i].Get()) {
			bitmap |= 1 << i;
		}
	}
	return bitmap;
}

void App::Task()
{
	Init();

	Buffer<100> startupMsg;
	TextPrinter p(startupMsg);
	p << "App Started\r\n";
	_comm.SendResponse(startupMsg);

	for(;;)
	{
		Buffer<Comm::MAX_CMD_LEN> cmdBuf;
		if (_comm.ReceiveCommand(cmdBuf, 10)) {
			HandleCommand(cmdBuf);
		}

		bool isValvesChanged = CheckValves();

		ControlWaterMeters(isValvesChanged);
	}
}

void App::AppendStatus(TextPrinter &p)
{
	int hour = 0, minute = 0, second = 0;
	_realTimer.Get(hour, minute, second);

	// Print zero-padded time
	if (hour < 10)   p << "0"; p << (long)hour   << ":";
	if (minute < 10) p << "0"; p << (long)minute << ":";
	if (second < 10) p << "0"; p << (long)second;

	p << " | wm1=" << _wmSim[0]._pulseCount
	  << " wm2=" << _wmSim[1]._pulseCount
	  << " wm3=" << _wmSim[2]._pulseCount
	  << " wm4=" << _wmSim[3]._pulseCount
	  << " wm5=" << _wmSim[4]._pulseCount;
}

bool App::CheckValves()
{
	bool isValvesOpened = false;

	for (int i = 0; i < VALVE_COUNT; ++i) {
		auto &valve = _valve[i];
		if (valve.IsChanged()) {
			Buffer<Comm::MAX_RESP_LEN> respBuf;
			TextPrinter response(respBuf);
			valve.PrintStatus(response);
			response << " at ";
			AppendStatus(response);
			response << "\r\n";
			_comm.SendResponse(respBuf);
		}

		if (valve.Get()) {
			isValvesOpened = true;
		}
	}

	return isValvesOpened;
}

void App::ControlWaterMeters(bool isValvesOpened)
{
	for (int wmIdx = 0; wmIdx < WM_SIM_COUNT; ++wmIdx) {
		auto &wm = _wmSim[wmIdx];
		// Each WM follows its corresponding valve (1↔1, 2↔2, ...)
		bool run = _valve[wmIdx].Get();

		WaterMeterSimulator::StateChange change = wm.Task(run);
		
		if (change != WaterMeterSimulator::StateChange::None) {
			Buffer<Comm::MAX_RESP_LEN> msg;
			TextPrinter p(msg);
			p << "wm " << wm._id << " ";
			if (change == WaterMeterSimulator::StateChange::Started) {
				wm._pulseCount = 0;
				p << "started working at ";
			} else {
				p << "stopped working at ";
			}
			AppendStatus(p);
			p << "\r\n";
			_comm.SendResponse(msg);
			if (change == WaterMeterSimulator::StateChange::Stopped) {
				wm._pulseCount = 0;
			}
		}
	}
}

void App::HandleCommand(const BufferView<> &cmd)
{
	TextScanner scanner(cmd);

	Buffer<Comm::MAX_RESP_LEN> respBuf;
	TextPrinter response(respBuf);

	Buffer<Comm::MAX_TOKEN_LEN> token1, token2;
	scanner >> token1 >> token2;

	if (!scanner.IsError()) {
		if (token1 == "system") {
			if (token2 == "init") {
				Init();
				response << "OK";
			}
		}
		else if (token1 == "set") {
			if (token2 == "time") {
				long hour, minute;
				scanner >> hour >> ":" >> minute;
				if (!scanner.IsError()) {
					_realTimer.Set(hour, minute, 0);
					response << "OK";
				}
			}
			else if (token2 == "dac") {
				long mv;
				scanner >> mv;
				if (!scanner.IsError()) {
					_dac.SetVoltage((float)mv / 1000.0f);
					response << "DAC set to " << mv << "mV";
				}
			}

		}
		else if (token1 == "get") {
			if (token2 == "time") {
				int hour, minute, second;
				if (_realTimer.Get(hour, minute, second)) {
					response << "sys time " << hour << ":" << minute << ":" << second;
				}
			}
			else if (token2 == "status") {
				uint32_t valveBitmap = GetValveBitmap();
				response << "valves status " << Hex(valveBitmap);
				for (auto wm: _wmSim) {
					wm.PrintStatus(response);
				}
			}
		}
		else if (token1 == "start") {
			if (token2 == "wm") {
				long id, cycleTimeMs;
				scanner >> id >> cycleTimeMs;
				if (!scanner.IsError() && id >= 1 && id <= WM_SIM_COUNT) {
					_wmSim[id - 1].SetStatus(WaterMeterSimulator::Status::Started, (uint32_t)cycleTimeMs);
					SaveWmCyclesToFlash();
					response << "wm " << id << " started";
				}
			}
		}
		else if (token1 == "stop") {
			if (token2 == "wm") {
				long id;
				scanner >> id;
				if (!scanner.IsError() && id >= 1 && id <= WM_SIM_COUNT) {
					_wmSim[id - 1].SetStatus(WaterMeterSimulator::Status::Stopped, 0);
					response << "wm " << id << " stopped";
				}
			}
		}
		else if (token1 == "trigger") {
			if (token2 == "wm") {
				long id, cycleTimeMs;
				scanner >> id >> cycleTimeMs;
				if (!scanner.IsError() && id >= 1 && id <= WM_SIM_COUNT) {
					_wmSim[id - 1].SetStatus(WaterMeterSimulator::Status::Triggered, (uint32_t)cycleTimeMs);
					SaveWmCyclesToFlash();
					response << "wm " << id << " triggered";
				}
			}
		}
		else if (token1 == "help") {
			Buffer<100> helpBuf;
			TextPrinter helpPrinter(helpBuf);
			
			helpPrinter << "Available Commands:\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();
			
			helpPrinter << " system init\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " set time HH:MM\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " get time\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " get status\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " start wm <id> <cycle_ms>\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " stop wm <id>\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			helpPrinter << " trigger wm <id> <cycle_ms>\r\n";
			_comm.SendResponse(helpBuf); helpBuf.Reset();

			response << "OK";
		}
	}

	if (respBuf.Len() <= 0 || scanner.IsError()) {
		response << "ERROR " << cmd;
		if (scanner.IsError()) {
			response << " (Scanner Error)";
		}
	}

	response << "\r\n";

	_comm.SendResponse(respBuf);
}
