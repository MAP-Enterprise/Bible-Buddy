import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  ActivityIndicator,
  Animated,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width } = Dimensions.get('window');
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Guest mode child ID for unauthenticated users
const GUEST_CHILD_ID = 'guest_child';

export default function HomeScreen() {
  const [isLoading, setIsLoading] = useState(false);
  const [hasChild, setHasChild] = useState(false);
  const bounceAnim = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    checkExistingChild();
    startBounceAnimation();
  }, []);

  const startBounceAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -15, duration: 1000, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  };

  const checkExistingChild = async () => {
    try {
      const childData = await AsyncStorage.getItem('currentChild');
      setHasChild(!!childData);
    } catch (error) {
      console.log('No existing child');
    }
  };

  const handleStartChat = async () => {
    // Start chat immediately in guest mode
    router.push('/chat');
  };

  const handleParentLogin = () => {
    router.push('/onboarding');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Logo Section */}
        <Animated.View style={[styles.logoContainer, { transform: [{ translateY: bounceAnim }] }]}>
          <Text style={styles.logoEmoji}>📖</Text>
          <Text style={styles.logoText}>Bible Buddy</Text>
          <Text style={styles.tagline}>Your friendly Bible companion!</Text>
        </Animated.View>

        {/* Description */}
        <View style={styles.descriptionContainer}>
          <Text style={styles.description}>
            Ask me anything about God, Jesus, or the Bible!{'\n'}
            I'm here to help you learn and grow in faith.
          </Text>
        </View>

        {/* Features */}
        <View style={styles.featuresContainer}>
          <View style={styles.featureItem}>
            <Ionicons name="chatbubbles" size={24} color="#4A90D9" />
            <Text style={styles.featureText}>Chat with Bible Buddy</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="mic" size={24} color="#4A90D9" />
            <Text style={styles.featureText}>Voice conversations</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="book" size={24} color="#4A90D9" />
            <Text style={styles.featureText}>Learn Bible stories</Text>
          </View>
          <View style={styles.featureItem}>
            <Ionicons name="shield-checkmark" size={24} color="#4A90D9" />
            <Text style={styles.featureText}>Safe for kids</Text>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.buttonsContainer}>
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleStartChat}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="chatbubble-ellipses" size={24} color="#fff" />
                <Text style={styles.primaryButtonText}>Start Chatting!</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handleParentLogin}
          >
            <Ionicons name="people" size={20} color="#4A90D9" />
            <Text style={styles.secondaryButtonText}>Parent Login</Text>
          </TouchableOpacity>
        </View>

        {/* Featured Teachers */}
        <View style={styles.teachersSection}>
          <Text style={styles.teachersTitle}>Wisdom from:</Text>
          <View style={styles.teachersList}>
            {['Apostle Selman', 'Stephanie Ike', 'Steven Furtick', 'Priscilla Shirer'].map((name, i) => (
              <View key={i} style={styles.teacherChip}>
                <Text style={styles.teacherName}>{name}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F0F7FF',
  },
  content: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  logoEmoji: {
    fontSize: 80,
    marginBottom: 8,
  },
  logoText: {
    fontSize: 36,
    fontWeight: '700',
    color: '#4A90D9',
  },
  tagline: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  descriptionContainer: {
    marginBottom: 24,
  },
  description: {
    fontSize: 16,
    textAlign: 'center',
    color: '#555',
    lineHeight: 24,
  },
  featuresContainer: {
    width: '100%',
    marginBottom: 24,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  featureText: {
    marginLeft: 12,
    fontSize: 15,
    color: '#333',
  },
  buttonsContainer: {
    width: '100%',
    marginBottom: 24,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4A90D9',
    paddingVertical: 18,
    borderRadius: 16,
    marginBottom: 12,
    shadowColor: '#4A90D9',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 10,
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#4A90D9',
  },
  secondaryButtonText: {
    color: '#4A90D9',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  teachersSection: {
    alignItems: 'center',
  },
  teachersTitle: {
    fontSize: 13,
    color: '#888',
    marginBottom: 8,
  },
  teachersList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
  },
  teacherChip: {
    backgroundColor: '#fff',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
  },
  teacherName: {
    fontSize: 11,
    color: '#666',
  },
});
