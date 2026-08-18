/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32l4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define B1_Pin GPIO_PIN_13
#define B1_GPIO_Port GPIOC
#define WM_SIM_0_Pin GPIO_PIN_0
#define WM_SIM_0_GPIO_Port GPIOC
#define WM_SIM_1_Pin GPIO_PIN_1
#define WM_SIM_1_GPIO_Port GPIOC
#define WM_SIM_2_Pin GPIO_PIN_2
#define WM_SIM_2_GPIO_Port GPIOC
#define WM_SIM_3_Pin GPIO_PIN_3
#define WM_SIM_3_GPIO_Port GPIOC
#define USART_TX_Pin GPIO_PIN_2
#define USART_TX_GPIO_Port GPIOA
#define USART_RX_Pin GPIO_PIN_3
#define USART_RX_GPIO_Port GPIOA
#define LD2_Pin GPIO_PIN_5
#define LD2_GPIO_Port GPIOA
#define WM_SIM_4_Pin GPIO_PIN_4
#define WM_SIM_4_GPIO_Port GPIOC
#define WM_SIM_5_Pin GPIO_PIN_5
#define WM_SIM_5_GPIO_Port GPIOC
#define VALVE_0_Pin GPIO_PIN_0
#define VALVE_0_GPIO_Port GPIOB
#define VALVE_1_Pin GPIO_PIN_1
#define VALVE_1_GPIO_Port GPIOB
#define VALVE_2_Pin GPIO_PIN_2
#define VALVE_2_GPIO_Port GPIOB
#define VALVE_3_Pin GPIO_PIN_10
#define VALVE_3_GPIO_Port GPIOB
#define VALVE_4_Pin GPIO_PIN_11
#define VALVE_4_GPIO_Port GPIOB
#define VALVE_5_Pin GPIO_PIN_12
#define VALVE_5_GPIO_Port GPIOB
#define VALVE_6_Pin GPIO_PIN_13
#define VALVE_6_GPIO_Port GPIOB
#define VALVE_7_Pin GPIO_PIN_14
#define VALVE_7_GPIO_Port GPIOB
#define VALVE_8_Pin GPIO_PIN_15
#define VALVE_8_GPIO_Port GPIOB
#define VALVE_9_Pin GPIO_PIN_6
#define VALVE_9_GPIO_Port GPIOC
#define VALVE_10_Pin GPIO_PIN_7
#define VALVE_10_GPIO_Port GPIOC
#define VALVE_11_Pin GPIO_PIN_8
#define VALVE_11_GPIO_Port GPIOC
#define VALVE_12_Pin GPIO_PIN_9
#define VALVE_12_GPIO_Port GPIOC
#define VALVE_13_Pin GPIO_PIN_8
#define VALVE_13_GPIO_Port GPIOA
#define VALVE_14_Pin GPIO_PIN_9
#define VALVE_14_GPIO_Port GPIOA
#define VALVE_15_Pin GPIO_PIN_10
#define VALVE_15_GPIO_Port GPIOA
#define TMS_Pin GPIO_PIN_13
#define TMS_GPIO_Port GPIOA
#define TCK_Pin GPIO_PIN_14
#define TCK_GPIO_Port GPIOA
#define SWO_Pin GPIO_PIN_3
#define SWO_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
