/*
 * DacControl.hpp
 *
 *  Created on: Dec 22, 2025
 *      Author: Copilot
 */

#pragma once

#include "stm32l4xx.h"

class DacControl
{
public:
	DacControl();

	void Init();
	void SetValue(uint16_t value); // 0-4095
	void SetVoltage(float voltage); // 0.0 - 3.3V

private:
	bool _isInitialized;
};
