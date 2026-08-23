using System.Collections.Generic;
using System.Globalization;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using UnityEngine;
using UnityEngine.SceneManagement;
using VRC.SDK3.Avatars.Components;

namespace Teyocesu.AvatarDoctor.Editor.Integrations.VRChat
{
    internal static class VRChatAvatarDescriptorBoundary
    {
        internal static void AppendCandidates(
            Scene scene,
            int loadedSceneIndex,
            List<AvatarDiscoveryCandidate> candidates)
        {
            if (candidates == null)
            {
                throw new System.ArgumentNullException(nameof(candidates));
            }

            if (!AvatarDiscoveryService.IsSceneEligible(scene))
            {
                return;
            }

            string normalizedScenePath = NormalizeScenePath(scene.path);
            bool isSavedScene = normalizedScenePath.Length > 0;
            string sceneIdentity = isSavedScene
                ? normalizedScenePath
                : string.Format(
                    CultureInfo.InvariantCulture,
                    "Unsaved scene {0}: {1}",
                    loadedSceneIndex,
                    scene.name);

            GameObject[] sceneRoots = scene.GetRootGameObjects();
            foreach (GameObject sceneRoot in sceneRoots)
            {
                VRCAvatarDescriptor[] descriptors =
                    sceneRoot.GetComponentsInChildren<VRCAvatarDescriptor>(true);
                foreach (VRCAvatarDescriptor descriptor in descriptors)
                {
                    if (!IsDescriptorLiveInScene(descriptor, scene))
                    {
                        continue;
                    }

                    GameObject avatarRoot = descriptor.gameObject;
                    int componentOrdinal = FindDescriptorOrdinal(
                        avatarRoot,
                        descriptor);
                    if (componentOrdinal < 0)
                    {
                        continue;
                    }

                    int[] siblingIndices = BuildSiblingIndexSequence(
                        avatarRoot.transform);
                    candidates.Add(new AvatarDiscoveryCandidate(
                        descriptor,
                        avatarRoot,
                        componentOrdinal,
                        avatarRoot.name,
                        sceneIdentity,
                        BuildHierarchyDisplayPath(avatarRoot.transform),
                        isSavedScene,
                        normalizedScenePath,
                        loadedSceneIndex,
                        scene.name,
                        siblingIndices,
                        descriptor.GetInstanceID(),
                        scene.handle));
                }
            }
        }

        internal static bool IsCandidateLive(
            AvatarDiscoveryCandidate candidate)
        {
            if (candidate == null)
            {
                return false;
            }

            VRCAvatarDescriptor descriptor =
                candidate.DescriptorIdentity as VRCAvatarDescriptor;
            if (descriptor == null || candidate.AvatarRoot == null)
            {
                return false;
            }

            Scene scene = descriptor.gameObject.scene;
            return descriptor.gameObject == candidate.AvatarRoot
                && scene.handle == candidate.SceneHandle
                && AvatarDiscoveryService.IsSceneEligible(scene)
                && FindDescriptorOrdinal(candidate.AvatarRoot, descriptor)
                    == candidate.DescriptorComponentOrdinal;
        }

        private static bool IsDescriptorLiveInScene(
            VRCAvatarDescriptor descriptor,
            Scene scene)
        {
            return descriptor != null
                && descriptor.gameObject != null
                && descriptor.gameObject.scene.handle == scene.handle
                && AvatarDiscoveryService.IsSceneEligible(
                    descriptor.gameObject.scene);
        }

        private static int FindDescriptorOrdinal(
            GameObject avatarRoot,
            VRCAvatarDescriptor descriptor)
        {
            VRCAvatarDescriptor[] descriptors =
                avatarRoot.GetComponents<VRCAvatarDescriptor>();
            for (int index = 0; index < descriptors.Length; index++)
            {
                if (descriptors[index] == descriptor)
                {
                    return index;
                }
            }

            return -1;
        }

        private static string NormalizeScenePath(string scenePath)
        {
            return string.IsNullOrEmpty(scenePath)
                ? string.Empty
                : scenePath.Replace('\\', '/');
        }

        private static int[] BuildSiblingIndexSequence(Transform transform)
        {
            List<int> reversedIndices = new List<int>();
            Transform current = transform;
            while (current != null)
            {
                reversedIndices.Add(current.GetSiblingIndex());
                current = current.parent;
            }

            reversedIndices.Reverse();
            return reversedIndices.ToArray();
        }

        private static string BuildHierarchyDisplayPath(Transform transform)
        {
            List<string> reversedSegments = new List<string>();
            Transform current = transform;
            while (current != null)
            {
                reversedSegments.Add(string.Format(
                    CultureInfo.InvariantCulture,
                    "{0} [{1}]",
                    current.name,
                    current.GetSiblingIndex()));
                current = current.parent;
            }

            reversedSegments.Reverse();
            return string.Join("/", reversedSegments);
        }
    }
}
