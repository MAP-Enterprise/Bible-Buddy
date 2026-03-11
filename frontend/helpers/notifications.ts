import { Platform } from 'react-native';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

let Notifications: any = null;

async function loadNotifications() {
  if (Notifications) return Notifications;
  try {
    Notifications = await import('expo-notifications');
    return Notifications;
  } catch {
    return null;
  }
}

export async function registerForPushNotifications(token: string): Promise<string | null> {
  const NotifModule = await loadNotifications();
  if (!NotifModule) {
    console.log('expo-notifications not available');
    return null;
  }

  // Push notifications need a physical device
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  try {
    if (Platform.OS === 'android') {
      await NotifModule.setNotificationChannelAsync('default', {
        name: 'Bible Buddy',
        importance: NotifModule.AndroidImportance?.MAX || 4,
        vibrationPattern: [0, 250, 250, 250],
      });
    }

    const { status: existingStatus } = await NotifModule.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await NotifModule.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('Push notification permission denied');
      return null;
    }

    const projectId =
      Constants?.expoConfig?.extra?.eas?.projectId ??
      (Constants as any)?.easConfig?.projectId;

    const pushToken = (await NotifModule.getExpoPushTokenAsync({ projectId })).data;

    // Register token with backend
    try {
      await fetch(`${BACKEND_URL}/api/notifications/register-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          token: pushToken,
          device_id: `${Platform.OS}_${Device.modelName || 'unknown'}`,
          platform: Platform.OS,
        }),
      });
    } catch (e) {
      console.log('Failed to register push token with backend:', e);
    }

    return pushToken;
  } catch (e) {
    console.log('Push notification setup error:', e);
    return null;
  }
}

export async function setupNotificationHandler() {
  const NotifModule = await loadNotifications();
  if (!NotifModule) return;

  NotifModule.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}
