#pragma once

#include "CoreMinimal.h"

/**
 * Tuning tables read from Content/Data/config.json by UMIDataSubsystem.
 * Everything here is already in Unreal units: centimetres, degrees, seconds (the file holds metres and radians).
 * This is the part of the file the bootstrap slice needs; the other tables are added by their packages.
 */

/** config.json "player.body" */
struct FMIPlayerBodyData
{
	float Radius = 0.f;        // cm, capsule radius
	float Height = 0.f;        // cm, standing collision height
	float CrouchHeight = 0.f;  // cm, crouched collision height
	float Eye = 0.f;           // cm above the feet, standing
	float CrouchEye = 0.f;     // cm above the feet, crouched
	float EyeRate = 0.f;       // 1/s, exponential rate of the eye height between stances
	float StepHeight = 0.f;    // cm, highest step taken without jumping
};

/** config.json "player.speed" */
struct FMIPlayerSpeedData
{
	float Walk = 0.f;          // cm/s
	float Sprint = 0.f;        // cm/s
	float Crouch = 0.f;        // cm/s
	float Ads = 0.f;           // cm/s while aiming
	float Backpedal = 0.f;     // factor on backward movement
};

/** config.json "player.accel" */
struct FMIPlayerAccelData
{
	float Ground = 0.f;        // cm/s^2
	float GroundStop = 0.f;    // cm/s^2
	float Air = 0.f;           // cm/s^2
	float AirStop = 0.f;       // cm/s^2
};

/** config.json "player.jump" */
struct FMIPlayerJumpData
{
	float Gravity = 0.f;       // cm/s^2, positive
	float Apex = 0.f;          // cm, height of a jump
	float Coyote = 0.f;        // s
	float Buffer = 0.f;        // s
	float Terminal = 0.f;      // cm/s

	/** Take-off speed that reaches Apex under Gravity, cm/s. */
	float LaunchSpeed() const { return FMath::Sqrt(2.f * Gravity * Apex); }
};

/** config.json "player.sprint" */
struct FMIPlayerSprintData
{
	float MinForward = 0.f;    // forward input must exceed this
	float MaxStrafe = 0.f;     // absolute strafe input must stay below this
	float MinSpeedFrac = 0.f;  // of walk speed: the "sprinting" flag needs at least this ground speed
};

/** config.json "player.fov": vertical degrees, as in the web game. */
struct FMIPlayerFovData
{
	float Base = 0.f;
	float Min = 0.f;
	float Max = 0.f;
	float SprintAdd = 0.f;
	float Ads = 0.f;
	float Rate = 0.f;          // 1/s
};

/** config.json "player.look" and "player.input" */
struct FMIPlayerLookData
{
	float PitchLimit = 0.f;           // degrees up and down
	float MouseDegreesPerCount = 0.f; // degrees of turn per mouse count at sensitivity 1
};

struct FMIPlayerData
{
	FMIPlayerBodyData Body;
	FMIPlayerSpeedData Speed;
	FMIPlayerAccelData Accel;
	FMIPlayerJumpData Jump;
	FMIPlayerSprintData Sprint;
	FMIPlayerFovData Fov;
	FMIPlayerLookData Look;
};

struct FMIConfigData
{
	FString Game;      // meta.game
	int32 Schema = 0;  // meta.schema
	int32 Seed = 0;    // meta.seed
	FMIPlayerData Player;
};
