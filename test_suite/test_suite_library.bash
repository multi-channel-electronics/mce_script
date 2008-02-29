#!/bin/bash

file_name="test_suite_library.bash"

function echo2_and_issue {
  test_log=$1
  cmd_str=$2
  
  echo "  > $cmd_str"|tee -a $test_log
  mce_ret=`$cmd_str`
}

function echo2 {
  test_log=$1
  str=$2
  echo "$str">>$test_log
  echo "$str"  
}

function test_result_analysis {
  tlog2=$1
  test_type_str2=$2
  interactive_mode2=$3
  autotest_type2=$4
  mce_ret2=$5
  autotest_lb2=$6
  autotest_ub2=$7
  tester_notes="fail"

  # Append/ output test information
  echo2 $tlog2 "$test_type_str2"  
  
  if [[ $test_type_str2 == No* ]]; then
    # The test does not exist, therefore results are not checked
    echo2 $tlog2 ""  
  else
    # Parse the tester's input.  Input must begin with "pass" or "fail".
    while [ 1 ]; do
      
# embed the interactive mode check after each test type      
      # If we are not in deaf mode, then wait for the reponse
      if [ $interactive_mode2 -eq 0 ]; then

        if [ $autotest_type2 -eq 0 -o $autotest_type2 -eq 2 ]; then
          # One value within a certain range
          echo2 $tlog2 "Pass criterion: between $autotest_lb2 and $autotest_ub2"          
        elif [ $autotest_type2 -eq 1 ]; then
          # Text
          echo2 $tlog2 "Pass criterion: contains $autotest_text"          
        elif [ $autotest_type2 -eq 3 ]; then
          # Does file exist
          echo2 $tlog2 "Pass criterion: does file exist"          
        else
          # skip check here
          :
        fi
        
        echo "Does the test [pass] or [fail]?  Type 'pass'/'fail' + comments, and press [ENTER]"
        read tester_notes

      else
      
        if [ $autotest_type2 -eq 0 ]; then
          # One value within a certain range
          if [ $mce_ret -ge $autotest_lb2 -a $mce_ret -le $autotest_ub2 ]; then
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        elif [ $autotest_type2 -eq 1 ]; then
          # Text
          substring=${mce_ret:1:2}
          if [ $substring = $autotest_text ]; then
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        elif [ $autotest_type2 -eq 2 ]; then
          # do multiple value checking here
#          substring=${mce_ret:0:1}
#          if [ mce_ret[0] -ge $autotest_lb2 ]; then
#            tester_notes="pass"
#          else
            tester_notes="fail"
#          fi
        elif [ $autotest_type2 -eq 3 ]; then
          if [ -s $data_filename ]; then
            # does file exist?
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        else
          # skip check here
          tester_notes="fail"
        fi
      fi
      
      if [[ $tester_notes == pass* ]]; then
        test_passes=$(($test_passes + 1))
        # Append the tester's ID and notes to the test log

        if [ $interactive_mode2 -eq 0 ]; then
          echo "$test_name : test $test_num : $tester_id : $tester_notes">>$tlog2
        else
          echo2 $tlog2 "$test_name : test $test_num : $tester_id : $tester_notes"
        fi        
        echo2 $tlog2 ""
        break
      elif [[ $tester_notes == fail* ]]; then
        test_failures=$(($test_failures + 1)) 
        # Append the tester's ID and notes to the test log
        if [ $interactive_mode2 -eq 0 ]; then
          echo "$test_name : test $test_num : $tester_id : $tester_notes">>$tlog2
        else
          echo2 $tlog2 "$test_name : test $test_num : $tester_id : $tester_notes"
        fi
        echo2 $tlog2 ""
        break
      elif [[ $tester_notes == none* ]]; then
        break
      fi
    done
  fi
}
