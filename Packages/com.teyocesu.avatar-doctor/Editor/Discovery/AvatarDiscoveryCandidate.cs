using System;
using UnityEngine;
using UnityObject = UnityEngine.Object;

namespace Teyocesu.AvatarDoctor.Editor.Discovery
{
    internal sealed class AvatarDiscoveryCandidate
    {
        private readonly int[] hierarchySiblingIndices;

        internal AvatarDiscoveryCandidate(
            UnityObject descriptorIdentity,
            GameObject avatarRoot,
            int descriptorComponentOrdinal,
            string displayName,
            string sceneIdentity,
            string hierarchyDisplayPath,
            bool isSavedScene,
            string normalizedSavedScenePath,
            int loadedSceneIndex,
            string sceneName,
            int[] hierarchySiblingIndices,
            int descriptorInstanceId,
            int sceneHandle)
        {
            if (descriptorIdentity == null)
            {
                throw new ArgumentNullException(nameof(descriptorIdentity));
            }

            if (avatarRoot == null)
            {
                throw new ArgumentNullException(nameof(avatarRoot));
            }

            if (descriptorComponentOrdinal < 0)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(descriptorComponentOrdinal));
            }

            DescriptorIdentity = descriptorIdentity;
            AvatarRoot = avatarRoot;
            DescriptorComponentOrdinal = descriptorComponentOrdinal;
            DisplayName = displayName
                ?? throw new ArgumentNullException(nameof(displayName));
            SceneIdentity = sceneIdentity
                ?? throw new ArgumentNullException(nameof(sceneIdentity));
            HierarchyDisplayPath = hierarchyDisplayPath
                ?? throw new ArgumentNullException(nameof(hierarchyDisplayPath));
            IsSavedScene = isSavedScene;
            NormalizedSavedScenePath = normalizedSavedScenePath
                ?? throw new ArgumentNullException(nameof(normalizedSavedScenePath));
            LoadedSceneIndex = loadedSceneIndex;
            SceneName = sceneName
                ?? throw new ArgumentNullException(nameof(sceneName));
            this.hierarchySiblingIndices = hierarchySiblingIndices != null
                ? (int[])hierarchySiblingIndices.Clone()
                : throw new ArgumentNullException(nameof(hierarchySiblingIndices));
            DescriptorInstanceId = descriptorInstanceId;
            SceneHandle = sceneHandle;
        }

        internal UnityObject DescriptorIdentity { get; }

        internal GameObject AvatarRoot { get; }

        internal int DescriptorComponentOrdinal { get; }

        internal string DisplayName { get; }

        internal string SceneIdentity { get; }

        internal string HierarchyDisplayPath { get; }

        internal bool IsSavedScene { get; }

        internal string NormalizedSavedScenePath { get; }

        internal int LoadedSceneIndex { get; }

        internal string SceneName { get; }

        internal int DescriptorInstanceId { get; }

        internal int SceneHandle { get; }

        internal int HierarchyDepth => hierarchySiblingIndices.Length;

        internal int GetHierarchySiblingIndex(int depth)
        {
            return hierarchySiblingIndices[depth];
        }
    }
}
