using System;
using System.Collections.Generic;
using NUnit.Framework;
using Teyocesu.AvatarDoctor.Editor.Discovery;
using UnityEngine;

namespace Teyocesu.AvatarDoctor.Editor.Tests
{
    internal sealed class AvatarDiscoveryOrderingTests
    {
        private GameObject identity;

        [SetUp]
        public void SetUp()
        {
            identity = new GameObject("Ordering Identity");
        }

        [TearDown]
        public void TearDown()
        {
            if (identity != null)
            {
                UnityEngine.Object.DestroyImmediate(identity);
            }
        }

        [Test]
        public void Compare_SortsSavedSceneBeforeUnsavedScene()
        {
            AvatarDiscoveryCandidate saved = CreateCandidate(
                true,
                "Assets/Z.unity",
                9,
                "Z",
                new[] { 9 },
                "Z [9]",
                0,
                1);
            AvatarDiscoveryCandidate unsaved = CreateCandidate(
                false,
                string.Empty,
                0,
                "A",
                new[] { 0 },
                "A [0]",
                0,
                2);

            Assert.That(Compare(saved, unsaved), Is.LessThan(0));
        }

        [Test]
        public void Compare_UsesOrdinalSavedScenePathComparison()
        {
            const string leftPath = "Assets/I.unity";
            const string rightPath = "Assets/ı.unity";
            AvatarDiscoveryCandidate left = CreateCandidate(
                true,
                leftPath,
                0,
                "Same",
                new[] { 0 },
                "Same [0]",
                0,
                1);
            AvatarDiscoveryCandidate right = CreateCandidate(
                true,
                rightPath,
                0,
                "Same",
                new[] { 0 },
                "Same [0]",
                0,
                2);

            Assert.That(
                Math.Sign(Compare(left, right)),
                Is.EqualTo(Math.Sign(StringComparer.Ordinal.Compare(
                    leftPath,
                    rightPath))));
        }

        [Test]
        public void Compare_OrdersUnsavedScenesByIndexThenOrdinalName()
        {
            AvatarDiscoveryCandidate earlierIndex = CreateCandidate(
                false,
                string.Empty,
                2,
                "Z",
                new[] { 0 },
                "Root [0]",
                0,
                1);
            AvatarDiscoveryCandidate laterIndex = CreateCandidate(
                false,
                string.Empty,
                10,
                "A",
                new[] { 0 },
                "Root [0]",
                0,
                2);
            AvatarDiscoveryCandidate nameA = CreateCandidate(
                false,
                string.Empty,
                4,
                "A",
                new[] { 0 },
                "Root [0]",
                0,
                3);
            AvatarDiscoveryCandidate nameB = CreateCandidate(
                false,
                string.Empty,
                4,
                "B",
                new[] { 0 },
                "Root [0]",
                0,
                4);

            Assert.That(Compare(earlierIndex, laterIndex), Is.LessThan(0));
            Assert.That(Compare(nameA, nameB), Is.LessThan(0));
        }

        [Test]
        public void Compare_UsesNumericSiblingIndexSequenceBeforeNames()
        {
            AvatarDiscoveryCandidate siblingTwo = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0, 2 },
                "Duplicate [0]/Duplicate [2]",
                0,
                1);
            AvatarDiscoveryCandidate siblingTen = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0, 10 },
                "Duplicate [0]/Duplicate [10]",
                0,
                2);

            Assert.That(Compare(siblingTwo, siblingTen), Is.LessThan(0));
        }

        [Test]
        public void Compare_UsesHierarchyPathOrdinalTieBreaker()
        {
            AvatarDiscoveryCandidate upper = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "Avatar [0]",
                0,
                1);
            AvatarDiscoveryCandidate lower = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "avatar [0]",
                0,
                2);

            Assert.That(Compare(upper, lower), Is.LessThan(0));
        }

        [Test]
        public void Compare_UsesComponentOrdinalThenInstanceId()
        {
            AvatarDiscoveryCandidate ordinalZero = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "Avatar [0]",
                0,
                50);
            AvatarDiscoveryCandidate ordinalOne = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "Avatar [0]",
                1,
                1);
            AvatarDiscoveryCandidate lowerInstanceId = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "Avatar [0]",
                0,
                10);

            Assert.That(Compare(ordinalZero, ordinalOne), Is.LessThan(0));
            Assert.That(Compare(lowerInstanceId, ordinalZero), Is.LessThan(0));
        }

        [Test]
        public void Sort_DuplicateDisplayNamesFollowCompleteCanonicalKey()
        {
            AvatarDiscoveryCandidate second = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 1 },
                "Duplicate [1]",
                0,
                2,
                "Duplicate");
            AvatarDiscoveryCandidate first = CreateCandidate(
                true,
                "Assets/Test.unity",
                0,
                "Test",
                new[] { 0 },
                "Duplicate [0]",
                0,
                1,
                "Duplicate");
            List<AvatarDiscoveryCandidate> candidates =
                new List<AvatarDiscoveryCandidate> { second, first };

            candidates.Sort(AvatarDiscoveryCandidateComparer.Instance);

            Assert.That(candidates, Is.EqualTo(new[] { first, second }));
        }

        private int Compare(
            AvatarDiscoveryCandidate left,
            AvatarDiscoveryCandidate right)
        {
            return AvatarDiscoveryCandidateComparer.Instance.Compare(left, right);
        }

        private AvatarDiscoveryCandidate CreateCandidate(
            bool isSavedScene,
            string savedPath,
            int sceneIndex,
            string sceneName,
            int[] siblingIndices,
            string hierarchyPath,
            int componentOrdinal,
            int instanceId,
            string displayName = "Avatar")
        {
            string sceneIdentity = isSavedScene
                ? savedPath
                : "Unsaved scene " + sceneIndex + ": " + sceneName;
            return new AvatarDiscoveryCandidate(
                identity,
                identity,
                componentOrdinal,
                displayName,
                sceneIdentity,
                hierarchyPath,
                isSavedScene,
                savedPath,
                sceneIndex,
                sceneName,
                siblingIndices,
                instanceId,
                1);
        }
    }
}
