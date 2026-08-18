/*
 * DacControl.cpp
 *
 *  Created on: Dec 22, 2025
 *      Author: Copilot
 */

#include "DacControl.hpp"
#include <algorithm>

DacControl::DacControl() : _isInitialized(false)
{
}

void DacControl::Init()
{
	if (_isInitialized) return;

	// 1. Enable DAC1 Clock
	RCC->APB1ENR1 |= RCC_APB1ENR1_DAC1EN;

	// 2. Configure PA4 as Analog (Mode 11)
	// Enable GPIOA Clock if not already enabled (it usually is)
	RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;

	// Set PA4 to Analog mode (11)
	GPIOA->MODER |= (3U << (4 * 2));
	// No Pull-up/Pull-down (00)
	GPIOA->PUPDR &= ~(3U << (4 * 2));

	// 3. Enable DAC Channel 1
	// Enable DAC Channel 1
	DAC1->CR |= DAC_CR_EN1;

	_isInitialized = true;
}

void DacControl::SetValue(uint16_t value)
{
	if (!_isInitialized) Init();

	value = std::min((uint16_t)4095, value);

	// Write to 12-bit right-aligned data holding register
	DAC1->DHR12R1 = value;
}

void DacControl::SetVoltage(float voltage)
{
	// Vref is typically 3.3V
	uint16_t value = (uint16_t)((voltage / 3.3f) * 4095.0f);
	SetValue(value);
}
