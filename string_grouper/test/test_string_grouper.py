import unittest
import pandas as pd
import numpy as np
from scipy.sparse.csr import csr_matrix
from string_grouper.string_grouper import DEFAULT_MIN_SIMILARITY, DEFAULT_MAX_N_MATCHES, DEFAULT_REGEX, \
    DEFAULT_NGRAM_SIZE, DEFAULT_N_PROCESSES, StringGrouperConfig, StringGrouper, StringGrouperNotFitException


class StringGrouperConfigTest(unittest.TestCase):
    def test_config_defaults(self):
        """Empty initialisation should set default values"""
        config = StringGrouperConfig()
        self.assertEqual(config.min_similarity, DEFAULT_MIN_SIMILARITY)
        self.assertEqual(config.max_n_matches, DEFAULT_MAX_N_MATCHES)
        self.assertEqual(config.regex, DEFAULT_REGEX)
        self.assertEqual(config.ngram_size, DEFAULT_NGRAM_SIZE)
        self.assertEqual(config.number_of_processes, DEFAULT_N_PROCESSES)

    def test_config_immutable(self):
        """Configurations should be immutable"""
        config = StringGrouperConfig()
        with self.assertRaises(Exception) as _:
            config.min_similarity = 0.1

    def test_config_non_default_values(self):
        """Configurations should be immutable"""
        config = StringGrouperConfig(min_similarity=0.1, max_n_matches=100, number_of_processes=1)
        self.assertEqual(0.1, config.min_similarity)
        self.assertEqual(100, config.max_n_matches)
        self.assertEqual(1, config.number_of_processes)


class StringGrouperTest(unittest.TestCase):
    def test_n_grams(self):
        """Should return all ngrams in a string"""
        test_series = pd.Series(pd.Series(['aa']))
        sg = StringGrouper(test_series)
        expected_result = ['McD', 'cDo', 'Don', 'ona', 'nal', 'ald', 'lds']
        self.assertListEqual(expected_result, sg.n_grams('McDonalds'))

    def test_build_matrix(self):
        """Should create a csr matrix only master"""
        test_series = pd.Series(['foo', 'bar', 'baz'])
        sg = StringGrouper(test_series)
        master, dupe = sg._get_tf_idf_matrices()
        c = csr_matrix([[0., 0., 1.]
                        , [1., 0., 0.]
                        , [0., 1., 0.]])
        np.testing.assert_array_equal(c.toarray(), master.toarray())
        np.testing.assert_array_equal(c.toarray(), dupe.toarray())

    def test_build_matrix_master_and_duplicates(self):
        """Should create a csr matrix for master and duplicates"""
        test_series_1 = pd.Series(['foo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foo', 'bar', 'bop'])
        sg = StringGrouper(test_series_1, test_series_2)
        master, dupe = sg._get_tf_idf_matrices()
        master_expected = csr_matrix([[0., 0., 0., 1.],
                                     [1., 0., 0., 0.],
                                     [0., 1., 0., 0.]])
        dupes_expected = csr_matrix([[0., 0., 0., 1.],
                                     [1., 0., 0., 0.],
                                     [0., 0., 1., 0.]])

        np.testing.assert_array_equal(master_expected.toarray(), master.toarray())
        np.testing.assert_array_equal(dupes_expected.toarray(), dupe.toarray())

    def test_build_matches(self):
        """Should create the cosine similarity matrix of two series"""
        test_series_1 = pd.Series(['foo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foo', 'bar', 'bop'])
        sg = StringGrouper(test_series_1, test_series_2)
        master, dupe = sg._get_tf_idf_matrices()

        expected_matches = np.array([[1., 0., 0.]
                                     , [0., 1., 0.]
                                     , [0., 0., 0.]])
        np.testing.assert_array_equal(expected_matches, sg._build_matches(master, dupe).toarray())

    def test_build_matches_list(self):
        """Should create the cosine similarity matrix of two series"""
        test_series_1 = pd.Series(['foo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foo', 'bar', 'bop'])
        sg = StringGrouper(test_series_1, test_series_2)
        sg = sg.fit()
        master = [0, 1]
        dupe_side = [0, 1]
        similarity = [1.0, 1.0]
        expected_df = pd.DataFrame({'master_side': master, 'dupe_side': dupe_side, 'similarity': similarity})
        pd.testing.assert_frame_equal(expected_df, sg._matches_list)

    def test_get_matches_two_dataframes(self):
        test_series_1 = pd.Series(['foo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foo', 'bar', 'bop'])
        sg = StringGrouper(test_series_1, test_series_2).fit()
        left_side = ['foo', 'bar']
        right_side = ['foo', 'bar']
        similarity = [1.0, 1.0]
        expected_df = pd.DataFrame({'left_side': left_side, 'right_side': right_side, 'similarity': similarity})
        pd.testing.assert_frame_equal(expected_df, sg.get_matches())

    def test_get_matches_single(self):
        test_series_1 = pd.Series(['foo', 'bar', 'baz', 'foo'])
        sg = StringGrouper(test_series_1)
        sg = sg.fit()
        left_side = ['foo', 'foo', 'bar', 'baz', 'foo', 'foo']
        right_side = ['foo', 'foo', 'bar', 'baz', 'foo', 'foo']
        similarity = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        expected_df = pd.DataFrame({'left_side': left_side, 'right_side': right_side, 'similarity': similarity})
        pd.testing.assert_frame_equal(expected_df, sg.get_matches())

    def test_get_groups_single_df(self):
        """Should return a pd.series object with the same lenght as the orignal df. The series object will contain
        a list of the grouped strings"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1)
        sg = sg.fit()
        result = sg.get_groups()
        expected_result = pd.Series(['foooo', 'bar', 'baz', 'foooo'])
        pd.testing.assert_series_equal(expected_result, result)

    def test_get_groups_single_df(self):
        """Should return a pd.series object with the same lenght as the orignal df. The series object will contain
        a list of the grouped strings"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz', 'foooob', 'bar', 'fooooc'])
        sg = StringGrouper(test_series_1)
        sg = sg.fit()
        result = sg.get_groups()
        expected_result = pd.Series(['foooo', 'bar', 'baz', 'foooo', 'bar', 'foooo'])
        pd.testing.assert_series_equal(expected_result, result)

    def test_get_groups_two_df(self):
        """Should return a pd.series object with the length of the dupes. The series will contain the master string
        that matches the dupe with the highest similarity"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1, test_series_2)
        sg = sg.fit()
        result = sg.get_groups()
        expected_result = pd.Series(['foooo', 'bar', 'baz', 'foooo'])
        pd.testing.assert_series_equal(expected_result, result)

    def test_get_groups_two_df_same_similarity(self):
        """Should return a pd.series object with the length of the dupes. If there are two dupes with the same
        similarity, the first one is chosen"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz', 'foooo'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1, test_series_2)
        sg = sg.fit()
        result = sg.get_groups()
        expected_result = pd.Series(['foooo', 'bar', 'baz', 'foooo'])
        pd.testing.assert_series_equal(expected_result, result)

    def test_get_groups_two_df_no_match(self):
        """Should return a pd.series object with the length of the dupes. If no match is found in dupes,
        the original will be returned"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz'])
        test_series_2 = pd.Series(['foooo', 'dooz', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1, test_series_2)
        sg = sg.fit()
        result = sg.get_groups()
        expected_result = pd.Series(['foooo', 'dooz', 'bar', 'baz', 'foooo'])
        pd.testing.assert_series_equal(expected_result, result)

    def test_get_groups_raises_exception(self):
        """Should raise an exception if called before the StringGrouper is fit"""
        test_series_1 = pd.Series(['foooo', 'bar', 'baz', 'foooo'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1, test_series_2)
        with self.assertRaises(StringGrouperNotFitException):
            _ = sg.get_groups()

    def test_clean_groups(self):
        """Should clean up groups where the group id index is not in the group"""
        orig_id = [0, 1, 2, 3]
        group_id = [0, 0, 1, 2]
        similarities = [1, 1, 1, 1]
        grouped_id_tuples = pd.DataFrame({'original_id': orig_id,
                                          'group_id': group_id,
                                          'min_similarity': similarities})
        expected_group_id = pd.Series([0, 0, 0, 0]).rename('group_id')
        result = StringGrouper._clean_groups(grouped_id_tuples).group_id
        pd.testing.assert_series_equal(expected_group_id, result)

    def test_add_match_raises_exception_if_string_not_present(self):
        test_series_1 = pd.Series(['foooo', 'no match', 'baz', 'foooo'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1).fit()
        sg2 = StringGrouper(test_series_1, test_series_2).fit()
        with self.assertRaises(ValueError):
            sg.add_match('doesnt exist', 'baz')
        with self.assertRaises(ValueError):
            sg.add_match('baz', 'doesnt exist')
        with self.assertRaises(ValueError):
            sg2.add_match('doesnt exist', 'baz')
        with self.assertRaises(ValueError):
            sg2.add_match('baz', 'doesnt exist')

    def test_add_match_single_occurence(self):
        """Should add the match if there are no exact duplicates"""
        test_series_1 = pd.Series(['foooo', 'no match', 'baz', 'foooo'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1).fit()
        sg.add_match('no match', 'baz')
        matches = sg.get_matches()
        matches = matches[(matches.left_side == 'no match') & (matches.right_side == 'baz')]
        self.assertEqual(1, matches.shape[0])
        sg2 = StringGrouper(test_series_1, test_series_2).fit()
        sg2.add_match('no match', 'bar')
        matches = sg2.get_matches()
        matches = matches[(matches.left_side == 'no match') & (matches.right_side == 'bar')]
        self.assertEqual(1, matches.shape[0])

    def test_add_match_single_group_matches_symmetric(self):
        """New matches that are added to a SG with only a master series should be symmetric"""
        test_series_1 = pd.Series(['foooo', 'no match', 'baz', 'foooo'])
        sg = StringGrouper(test_series_1).fit()
        sg.add_match('no match', 'baz')
        matches = sg.get_matches()
        matches_1 = matches[(matches.left_side == 'no match') & (matches.right_side == 'baz')]
        self.assertEqual(1, matches_1.shape[0])
        matches_2 = matches[(matches.left_side == 'baz') & (matches.right_side == 'no match')]
        self.assertEqual(1, matches_2.shape[0])

    def test_add_match_multiple_occurences(self):
        """Should add multiple matches if there are exact duplicates"""
        test_series_1 = pd.Series(['foooo', 'no match', 'baz', 'foooo'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1, test_series_2).fit()
        sg.add_match('foooo', 'baz')
        matches = sg.get_matches()
        matches = matches[(matches.left_side == 'foooo') & (matches.right_side == 'baz')]
        self.assertEqual(2, matches.shape[0])

    def test_remove_match(self):
        """Should remove a match"""
        test_series_1 = pd.Series(['foooo', 'no match', 'baz', 'foooob'])
        test_series_2 = pd.Series(['foooo', 'bar', 'baz', 'foooob'])
        sg = StringGrouper(test_series_1).fit()
        sg.remove_match('foooo', 'foooob')
        matches = sg.get_matches()
        matches_1 = matches[(matches.left_side == 'foooo') & (matches.right_side == 'foooob')]
        # In the case of only a master series, the matches are recursive, so both variants are to be removed
        matches_2 = matches[(matches.left_side == 'foooob') & (matches.right_side == 'foooo')]
        self.assertEqual(0, matches_1.shape[0])
        self.assertEqual(0, matches_2.shape[0])

        sg2 = StringGrouper(test_series_1, test_series_2).fit()
        sg2.remove_match('foooo', 'foooob')
        matches = sg2.get_matches()
        matches = matches[(matches.left_side == 'foooo') & (matches.right_side == 'foooob')]
        self.assertEqual(0, matches.shape[0])

    def test_string_grouper_type_error(self):
        """StringGrouper should raise an typeerror master or duplicates are not a series of strings"""
        with self.assertRaises(TypeError):
            _ = StringGrouper('foo', 'bar')
        with self.assertRaises(TypeError):
            _ = StringGrouper(pd.Series(['foo', 'bar']), pd.Series(['foo', 1]))
        with self.assertRaises(TypeError):
            _ = StringGrouper(pd.Series(['foo', np.nan]), pd.Series(['foo', 'j']))

if __name__ == '__main__':
    unittest.main()
